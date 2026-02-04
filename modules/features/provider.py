import json
from typing import Any, Callable, Optional, Sequence, Union

import pyarrow
from feast import OnDemandFeatureView
from feast.entity import Entity
from feast.feature_store import RepoConfig
from feast.feature_view import FeatureView
from feast.infra.passthrough_provider import PassthroughProvider

from shared.utils import JSONEncoder
from shared.utils.logging import log_debug, log_error

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None


class FediwayProvider(PassthroughProvider):
    def update_infra(
        self,
        project: str,
        tables_to_delete: Sequence[FeatureView],
        tables_to_keep: Sequence[Union[FeatureView, OnDemandFeatureView]],
        entities_to_delete: Sequence[Entity],
        entities_to_keep: Sequence[Entity],
        partial: bool,
    ):
        super().update_infra(
            project,
            tables_to_delete,
            tables_to_keep,
            entities_to_delete,
            entities_to_keep,
            partial,
        )

        # TODO: create topics

    @classmethod
    def offline_write_batch(
        cls,
        config: RepoConfig,
        feature_view: FeatureView,
        data: pyarrow.Table,
        progress: Optional[Callable[[int], Any]],
    ) -> None:
        if isinstance(feature_view, OnDemandFeatureView):
            return

        if "offline_store" not in feature_view.tags:
            return

        producer = KafkaProducer(
            bootstrap_servers=config.offline_store.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, cls=JSONEncoder).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k else None,
            max_in_flight_requests_per_connection=5,  # Parallel sends
            acks=1,  # Leader acknowledgment
            retries=3,
        )

        futures = []

        for row in data.to_pylist():
            key = ",".join([str(row[e]) for e in feature_view.entities])

            future = producer.send(feature_view.tags["offline_store"], key=key, value=row)

            futures.append(future)

        successful_deliveries = 0
        for future in futures:
            try:
                future.get(timeout=10)
                successful_deliveries += 1
            except Exception as e:
                log_error("Kafka message delivery failed", module="features", error=str(e))

        # Ensure all messages are sent
        producer.flush()

        log_debug(
            "Ingested features to offline store",
            module="features",
            feature_view=feature_view.name,
            successful=successful_deliveries,
            total=len(data),
        )
