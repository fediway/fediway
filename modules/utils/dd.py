import numpy as np
import pandas as pd

import dask.dataframe as dd
from dask.base import compute as dask_compute
from dask.dataframe.io.sql import _read_sql_chunk
from dask.dataframe import methods
from dask.dataframe._compat import PANDAS_GE_300
from dask.dataframe.utils import pyarrow_strings_enabled
from dask.delayed import delayed, tokenize
from dask.utils import parse_bytes

import modules.utils as utils


def read_sql_join_query(
    sql,
    con,
    index_col,
    divisions=None,
    npartitions=None,
    limits=None,
    bytes_per_chunk="256 MiB",
    head_rows=5,
    meta=None,
    engine_kwargs=None,
    sql_append="",
    **kwargs,
):
    """
    Read SQL query into a DataFrame.

    If neither ``divisions`` or ``npartitions`` is given, the memory footprint of the
    first few rows will be determined, and partitions of size ~256MB will
    be used.

    Parameters
    ----------
    sql : SQLAlchemy Selectable
        SQL query to be executed. TextClause is not supported
    con : str
        Full sqlalchemy URI for the database connection
    index_col : str
        Column which becomes the index, and defines the partitioning. Should
        be a indexed column in the SQL server, and any orderable type. If the
        type is number or time, then partition boundaries can be inferred from
        ``npartitions`` or ``bytes_per_chunk``; otherwise must supply explicit
        ``divisions``.
    divisions: sequence
        Values of the index column to split the table by. If given, this will
        override ``npartitions`` and ``bytes_per_chunk``. The divisions are the value
        boundaries of the index column used to define the partitions. For
        example, ``divisions=list('acegikmoqsuwz')`` could be used to partition
        a string column lexographically into 12 partitions, with the implicit
        assumption that each partition contains similar numbers of records.
    npartitions : int
        Number of partitions, if ``divisions`` is not given. Will split the values
        of the index column linearly between ``limits``, if given, or the column
        max/min. The index column must be numeric or time for this to work
    limits: 2-tuple or None
        Manually give upper and lower range of values for use with ``npartitions``;
        if None, first fetches max/min from the DB. Upper limit, if
        given, is inclusive.
    bytes_per_chunk : str or int
        If both ``divisions`` and ``npartitions`` is None, this is the target size of
        each partition, in bytes
    head_rows : int
        How many rows to load for inferring the data-types, and memory per row
    meta : empty DataFrame or None
        If provided, do not attempt to infer dtypes, but use these, coercing
        all chunks on load
    engine_kwargs : dict or None
        Specific db engine parameters for sqlalchemy
    kwargs : dict
        Additional parameters to pass to `pd.read_sql()`

    Returns
    -------
    dask.dataframe

    See Also
    --------
    read_sql_table : Read SQL database table into a DataFrame.
    """
    import sqlalchemy as sa

    if not isinstance(con, str):
        raise TypeError(
            "'con' must be of type str, not "
            + str(type(con))
            + "Note: Dask does not support SQLAlchemy connectables here"
        )
    if index_col is None:
        raise ValueError("Must specify index column to partition on")
    if not isinstance(index_col, (str, sa.Column, sa.sql.elements.ColumnClause)):
        raise ValueError(
            "'index_col' must be of type str or sa.Column, not " + str(type(index_col))
        )
    if not head_rows > 0:
        if meta is None:
            raise ValueError("Must provide 'meta' if 'head_rows' is 0")
        if divisions is None and npartitions is None:
            raise ValueError(
                "Must provide 'divisions' or 'npartitions' if 'head_rows' is 0"
            )
    if divisions and npartitions:
        raise TypeError("Must supply either 'divisions' or 'npartitions', not both")

    engine_kwargs = {} if engine_kwargs is None else engine_kwargs
    engine = sa.create_engine(con, **engine_kwargs)

    index = (
        sa.Column(index_col)
        if isinstance(index_col, str)
        else sa.Column(index_col.name, index_col.type)
    )

    kwargs["index_col"] = index.name.split(".")[-1]

    if head_rows > 0:
        # derive metadata from first few rows
        q = str(sql.compile(engine, compile_kwargs={"literal_binds": True}))
        q += f" {sql_append} LIMIT {head_rows}"
        head = pd.read_sql(q, engine, **kwargs)

        if len(head) == 0:
            # no results at all
            return dd.from_pandas(head, npartitions=1)

        if pyarrow_strings_enabled():
            from dask.dataframe._pyarrow import to_pyarrow_string

            # to estimate partition size with pyarrow strings
            head = to_pyarrow_string(head)

        bytes_per_row = (head.memory_usage(deep=True, index=True)).sum() / head_rows
        if meta is None:
            meta = head.iloc[:0]

    if divisions is None:
        if limits is None:
            # calculate max and min for given index
            with utils.duration("limits: {:.3f}"):
                q = str(sql.compile(engine, compile_kwargs={"literal_binds": True}))
                q = sa.sql.select(
                    sa.sql.func.max(sa.Column(index_col.split(".")[-1])),
                    sa.sql.func.min(sa.Column(index_col.split(".")[-1])),
                ).select_from(sa.text("(" + q + f" {sql_append})"))
                minmax = pd.read_sql(q, engine)
                maxi, mini = minmax.iloc[0]
                dtype = minmax.dtypes["max_1"]
        else:
            mini, maxi = limits
            dtype = pd.Series(limits).dtype

        if npartitions is None:
            with utils.duration("npartitions: {:.3f}"):
                q = str(sql.compile(engine, compile_kwargs={"literal_binds": True}))
                q = sa.sql.select(
                    sa.sql.func.count(sa.Column(index_col.split(".")[-1]))
                ).select_from(sa.text("(" + q + f" {sql_append})"))
                count = pd.read_sql(q, engine)["count_1"][0]
                npartitions = (
                    int(round(count * bytes_per_row / parse_bytes(bytes_per_chunk)))
                    or 1
                )
        if dtype.kind == "M":
            divisions = methods.tolist(
                pd.date_range(
                    start=mini,
                    end=maxi,
                    freq="%is" % ((maxi - mini).total_seconds() / npartitions),
                )
            )
            divisions[0] = mini
            divisions[-1] = maxi
        elif dtype.kind in ["i", "u", "f"]:
            divisions = np.linspace(mini, maxi, npartitions + 1, dtype=dtype).tolist()
        else:
            raise TypeError(
                'Provided index column is of type "{}".  If divisions is not provided the '
                "index column type must be numeric or datetime.".format(dtype)
            )

    parts = []
    lowers, uppers = divisions[:-1], divisions[1:]
    sql = str(sql.compile(engine, compile_kwargs={"literal_binds": True}))

    for i, (lower, upper) in enumerate(zip(lowers, uppers)):
        # cond = index <= upper if i == len(lowers) - 1 else index < upper
        q = sql + f" AND {index} >= {lower} AND "
        if i == len(lowers):
            q += f"{index} <= {upper}"
        else:
            q += f"{index} < {upper}"
        q += f" {sql_append}"
        # q = sql.where(sa.sql.and_(index >= lower, cond))
        parts.append(
            delayed(_read_sql_chunk)(
                q, con, meta, engine_kwargs=engine_kwargs, **kwargs
            )
        )

    engine.dispose()

    return dd.from_delayed(parts, meta, divisions)
