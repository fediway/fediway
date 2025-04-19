
import bytewax.operators as op
from bytewax.dataflow import Dataflow
from bytewax.testing import TestingSource
from bytewax.connectors.stdio import StdOutSink

import json

from config import config

# fs = FeatureStore(repo_path=config.feast.feast_repo_path)

# broker = KafkaInput(
#     brokers=["localhost:9092"], 
#     topics=["debezium_likes"],
# )

inp = [0, 1, 2]

flow = Dataflow("test")
input_stream = op.input('int', flow, TestingSource)

# flow.input("kafka-in", broker)

if __name__ == "__main__":
    pass