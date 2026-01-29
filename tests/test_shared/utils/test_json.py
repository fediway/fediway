import json

import numpy as np
import pytest

from shared.utils.json import JSONEncoder


def test_encodes_numpy_integer():
    data = {"value": np.int64(42)}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"value": 42}'


def test_encodes_numpy_int32():
    data = {"value": np.int32(123)}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"value": 123}'


def test_encodes_numpy_floating():
    data = {"value": np.float64(3.14)}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"value": 3.14}'


def test_encodes_numpy_nan_as_nan():
    # Note: numpy floats get converted to Python floats before default() is called,
    # so NaN becomes JavaScript NaN (not valid JSON, but matches json.dumps behavior)
    data = {"value": np.float64("nan")}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"value": NaN}'


def test_encodes_numpy_array():
    data = {"values": np.array([1, 2, 3])}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"values": [1, 2, 3]}'


def test_encodes_numpy_2d_array():
    data = {"matrix": np.array([[1, 2], [3, 4]])}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"matrix": [[1, 2], [3, 4]]}'


def test_encodes_tuple_as_list():
    data = {"coords": (1, 2, 3)}
    result = json.dumps(data, cls=JSONEncoder)
    assert result == '{"coords": [1, 2, 3]}'


def test_encodes_nested_tuple():
    data = {"nested": ((1, 2), (3, 4))}
    result = json.dumps(data, cls=JSONEncoder)
    parsed = json.loads(result)
    assert parsed["nested"] == [[1, 2], [3, 4]]


def test_encodes_mixed_numpy_types():
    data = {
        "int": np.int64(10),
        "float": np.float32(2.5),
        "array": np.array([1, 2]),
    }
    result = json.dumps(data, cls=JSONEncoder)
    parsed = json.loads(result)
    assert parsed["int"] == 10
    assert parsed["float"] == 2.5
    assert parsed["array"] == [1, 2]


def test_passes_through_standard_types():
    data = {
        "string": "hello",
        "int": 42,
        "float": 3.14,
        "bool": True,
        "null": None,
        "list": [1, 2, 3],
        "dict": {"nested": "value"},
    }
    result = json.dumps(data, cls=JSONEncoder)
    parsed = json.loads(result)
    assert parsed == data


def test_raises_on_unsupported_type():
    class CustomObject:
        pass

    data = {"obj": CustomObject()}
    with pytest.raises(TypeError):
        json.dumps(data, cls=JSONEncoder)
