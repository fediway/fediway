
import os
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StringType, IntegerType, TimestampType, LongType, StructField, ArrayType, FloatType
)
from pyspark.sql import functions as F

from config import config
from app.features import FEATURE_VIEWS
from app.modules.spark import (
    parse_debezium_payload, 
    get_spark_streaming_session, 
    get_kafka_stream_reader,
    get_schema_from_fv
)

def get_fv_by_name(name):
    for fv in FEATURE_VIEWS:
        if fv.name != name:
            continue
        return fv

def process_features(spark, topic, fv, schema, callback = None):
    df = get_kafka_stream_reader(
        spark, 
        bootstrap_servers=config.kafka.kafka_bootstrap_servers, 
        topic=topic,
    )

    # process CDC events
    df = (
        parse_debezium_payload(df, schema)
        .filter(F.col("op").isin(["c", "u"])) # only keep creates/updates
        .select(
            F.least(
                (F.col("after.event_time") / 1000).cast("timestamp"), 
                (F.col("ts_ms") / 1000).cast("timestamp")
            ).alias("true_event_time"),
            F.col("after.*"),
        )
        .drop("event_time")
        .withColumnRenamed("true_event_time","event_time")
        .withColumn("year", F.year(F.col("event_time")))
        .withColumn("month", F.month(F.col("event_time")))
        .withColumn("day", F.day(F.col("event_time")))
    )

    if callback is not None:
        df = callback(df)

    for field in fv.schema:
        df = df.withColumnRenamed(field.name.split('.')[-1], field.name)
    
    # return (
    #     df.writeStream
    #     .outputMode("append")
    #     .format("console")
    #     .option("truncate", False)
    #     .start()
    # )

    return (
        df.writeStream 
        .outputMode("append")
        .format("parquet")
        .option("path", f"{config.feast.feast_offline_store_path}/{topic}")
        .option("checkpointLocation", f"{config.feast.feast_spark_checkpoint_location}/{topic}")
        .partitionBy("year", "month", "day")
        .trigger(processingTime="5 seconds")
        .start()
    )
    
class Parser():
    def __init__(self, topic, fv):
        self.topic = topic
        self.fv = fv

    def parse_schema(self, schema):
        return schema

    def parse_df(self, df):
        return df

class EngagementParser(Parser):
    def parse_df(self, df):
        for field in self.fv.schema:
            column = field.name.split('.')[-1]
            df = df.withColumn(column, F.col(column).cast("int"))
        return df

class LatestEmbeddingsParser(Parser):
    '''
    Feast does not support nested array types, so the 2d embeddings array will be flattened to 1d here.
    '''

    def parse_schema(self, schema):
        dtype = ArrayType(ArrayType(FloatType()))
        return StructType([
            StructField(
                f.name, 
                dtype if f.name.endswith('embeddings') else f.dataType, 
                f.nullable, 
                f.metadata
            )
            for f in schema.fields
        ])

    def parse_df(self, df):
        return df.withColumn("embeddings", F.flatten("embeddings"))

feature_topics = {
    # engagement features
    'author_engagement_all_features': ('author_engagement_all', EngagementParser),
    'author_engagement_is_favourite_features': ('author_engagement_is_favourite', EngagementParser),
    'author_engagement_is_reblog_features': ('author_engagement_is_reblog', EngagementParser),
    'author_engagement_is_reply_features': ('author_engagement_is_reply', EngagementParser),
    'author_engagement_has_image_features': ('author_engagement_has_image', EngagementParser),
    'author_engagement_has_gifv_features': ('author_engagement_has_gifv', EngagementParser),
    'author_engagement_has_video_features': ('author_engagement_has_video', EngagementParser),
    'account_engagement_all_features': ('account_engagement_all', EngagementParser),
    'account_engagement_is_favourite_features': ('account_engagement_is_favourite', EngagementParser),
    'account_engagement_is_reblog_features': ('account_engagement_is_reblog', EngagementParser),
    'account_engagement_is_reply_features': ('account_engagement_is_reply', EngagementParser),
    'account_engagement_has_image_features': ('account_engagement_has_image', EngagementParser),
    'account_engagement_has_gifv_features': ('account_engagement_has_gifv', EngagementParser),
    'account_engagement_has_video_features': ('account_engagement_has_video', EngagementParser),
    'account_author_engagement_all_features': ('account_author_engagement_all', EngagementParser),
    'account_author_engagement_is_favourite_features': ('account_author_engagement_is_favourite', EngagementParser),
    'account_author_engagement_is_reblog_features': ('account_author_engagement_is_reblog', EngagementParser),
    'account_author_engagement_is_reply_features': ('account_author_engagement_is_reply', EngagementParser),
    'account_author_engagement_has_image_features': ('account_author_engagement_has_image', EngagementParser),
    'account_author_engagement_has_gifv_features': ('account_author_engagement_has_gifv', EngagementParser),
    'account_author_engagement_has_video_features': ('account_author_engagement_has_video', EngagementParser),

    # latest account embeddings
    'latest_account_favourites_embeddings': ('latest_account_favourites_embeddings', LatestEmbeddingsParser),
    'latest_account_reblogs_embeddings': ('latest_account_reblogs_embeddings', LatestEmbeddingsParser),
    'latest_account_replies_embeddings': ('latest_account_replies_embeddings', LatestEmbeddingsParser),
}

spark = get_spark_streaming_session(
    app_name="OfflineFeatureStore",
    s3_enabled=config.feast.feast_offline_store_path.startswith('s3a'),
    s3_endpoint=config.feast.feast_offline_store_s3_endpoint
)

# streaming queries
queries = []

for topic, fv_name in feature_topics.items():
    parser = None
    parse_df = None

    # get parser
    if type(fv_name) == tuple:
        fv_name, parser = fv_name
    
    # get schema
    fv = get_fv_by_name(fv_name)
    assert fv is not None

    # initialize parser
    if parser is not None:
        parser = parser(topic=topic, fv=fv)
        parse_df = parser.parse_df

    schema = get_schema_from_fv(fv)
    if parser is not None:
        schema = parser.parse_schema(schema)

    query = process_features(spark, topic, fv, schema, parse_df)
    queries.append(query)

# Wait for all streams to terminate
for query in queries:
    query.awaitTermination()