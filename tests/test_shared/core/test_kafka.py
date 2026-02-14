from unittest.mock import MagicMock, patch

from shared.core.kafka import get_kafka_producer


def test_get_kafka_producer_returns_none_when_not_installed():
    with patch("shared.core.kafka.KafkaProducer", None):
        result = get_kafka_producer()
        assert result is None


def test_get_kafka_producer_returns_none_on_connection_error():
    mock_producer_class = MagicMock(side_effect=Exception("NoBrokersAvailable"))

    with patch("shared.core.kafka.KafkaProducer", mock_producer_class):
        result = get_kafka_producer()
        assert result is None


def test_get_kafka_producer_returns_producer_on_success():
    mock_instance = MagicMock()
    mock_producer_class = MagicMock(return_value=mock_instance)

    with patch("shared.core.kafka.KafkaProducer", mock_producer_class):
        result = get_kafka_producer()
        assert result is mock_instance
