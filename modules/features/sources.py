import json
from typing import Dict, Iterable, Optional, Tuple

from feast.data_source import DataSource
from feast.infra.utils.postgres.connection_utils import _get_conn
from feast.protos.feast.core.DataSource_pb2 import DataSource as DataSourceProto
from feast.repo_config import RepoConfig
from feast.type_map import pg_type_code_to_pg_type


class RisingWaveOptions:
    def __init__(
        self,
        name: Optional[str],
        topic: Optional[str],
        table: Optional[str],
    ):
        self._name = name or ""
        self._topic = topic or ""
        self._table = table or ""

    @classmethod
    def from_proto(cls, risingwave_options_proto: DataSourceProto.CustomSourceOptions):
        config = json.loads(risingwave_options_proto.configuration.decode("utf8"))

        return cls(name=config["name"], topic=config["topic"], table=config["table"])

    def to_proto(self) -> DataSourceProto.CustomSourceOptions:
        return DataSourceProto.CustomSourceOptions(
            configuration=json.dumps(
                {"name": self._name, "topic": self._topic, "table": self._table}
            ).encode()
        )


class RisingWaveSource(DataSource):
    def __init__(
        self,
        name: Optional[str] = None,
        table: Optional[str] = None,
        topic: Optional[str] = None,
        timestamp_field: Optional[str] = "",
        created_timestamp_column: Optional[str] = "",
        field_mapping: Optional[Dict[str, str]] = None,
        description: Optional[str] = "",
        tags: Optional[Dict[str, str]] = None,
        owner: Optional[str] = "",
    ):
        self._options = RisingWaveOptions(name=name, topic=topic, table=table)

        super().__init__(
            name=name,
            timestamp_field=timestamp_field,
            created_timestamp_column=created_timestamp_column,
            field_mapping=field_mapping,
            description=description,
            tags=tags,
            owner=owner,
        )

    @property
    def table(self):
        return self._options._table

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if not isinstance(other, RisingWaveSource):
            return False

        return (
            super().__eq__(other)
            and self.timestamp_field == other.timestamp_field
            and self.created_timestamp_column == other.created_timestamp_column
            and self.field_mapping == other.field_mapping
        )

    @classmethod
    def from_proto(cls, data_source: DataSourceProto):
        assert data_source.HasField("custom_options")

        options = json.loads(data_source.custom_options.configuration)

        return cls(
            name=options["name"],
            table=options["table"],
            field_mapping=dict(data_source.field_mapping),
            timestamp_field=data_source.timestamp_field,
            created_timestamp_column=data_source.created_timestamp_column,
            description=data_source.description,
            tags=dict(data_source.tags),
            owner=data_source.owner,
        )

    def to_proto(self) -> DataSourceProto:
        data_source_proto = DataSourceProto(
            name=self.name,
            type=DataSourceProto.CUSTOM_SOURCE,
            data_source_class_type="modules.features.sources.RisingWaveSource",
            field_mapping=self.field_mapping,
            custom_options=self._options.to_proto(),
            description=self.description,
            tags=self.tags,
            owner=self.owner,
        )

        data_source_proto.timestamp_field = self.timestamp_field
        data_source_proto.created_timestamp_column = self.created_timestamp_column

        return data_source_proto

    def validate(self, config: RepoConfig):
        pass

    def get_table_column_names_and_types(self, config: RepoConfig) -> Iterable[Tuple[str, str]]:
        with _get_conn(config.offline_store) as conn, conn.cursor() as cur:
            query = f"SELECT * FROM {self._options._table} AS sub LIMIT 0"
            cur.execute(query)
            if not cur.description:
                raise ZeroColumnQueryResult(query)

            return ((c.name, pg_type_code_to_pg_type(c.type_code)) for c in cur.description)
