
import os
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StringType, IntegerType, TimestampType, LongType
from pyspark.sql import functions as F

from config import config
from app.features import FEATURE_VIEWS
from app.modules.spark import parse_debezium_payload

def get_fv_by_name(name):
    for fv in FEATURE_VIEWS:
        if fv.name != name:
            continue
        return fv

def get_schema(fv_name: str):
    fv = get_fv_by_name(fv_name)
    assert fv is not None

    schema = StructType()

    schema.add("event_time", LongType())
    for entity in fv.entities:
        schema.add(entity if type(entity) == str else entity.name, LongType())
    for field in fv.schema:
        schema.add(field.name.split('.')[-1], StringType())
    
    return schema

def process_debezium_stream(topic, schema):
    df = (
        spark.readStream 
        .format("kafka") 
        .option("kafka.bootstrap.servers", config.kafka.kafka_bootstrap_servers)
        # .option("kafka.group.id", topic)
        .option("subscribe", topic) 
        .option("startingOffsets", "earliest") 
        .load()
    )

    # process CDC events
    processed = (
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

    # query = (
    #     processed.writeStream
    #     .outputMode("append")
    #     .format("console")
    #     .option("truncate", False)
    #     .start()
    # )

    # write
    query = (
        processed.writeStream 
        .outputMode("append")
        .format("parquet")
        .option("path", f"{config.feast.feast_offline_store_path}/{topic}")
        .option("checkpointLocation", f"{config.feast.feast_spark_checkpoint_location}/{topic}")
        .partitionBy("year", "month", "day")
        .trigger(processingTime="5 seconds")
        .start()
    )
    
    return query

engagement_feature_topics = {
    'author_engagement_all_features': 'author_engagement_all',
    'author_engagement_is_favourite_features': 'author_engagement_is_favourite',
    'author_engagement_is_reblog_features': 'author_engagement_is_reblog',
    'author_engagement_is_reply_features': 'author_engagement_is_reply',
    'author_engagement_has_image_features': 'author_engagement_has_image',
    'author_engagement_has_gifv_features': 'author_engagement_has_gifv',
    'author_engagement_has_video_features': 'author_engagement_has_video',
    'account_engagement_all_features': 'account_engagement_all',
    'account_engagement_is_favourite_features': 'account_engagement_is_favourite',
    'account_engagement_is_reblog_features': 'account_engagement_is_reblog',
    'account_engagement_is_reply_features': 'account_engagement_is_reply',
    'account_engagement_has_image_features': 'account_engagement_has_image',
    'account_engagement_has_gifv_features': 'account_engagement_has_gifv',
    'account_engagement_has_video_features': 'account_engagement_has_video',
    'account_author_engagement_all_features': 'account_author_engagement_all',
    'account_author_engagement_is_favourite_features': 'account_author_engagement_is_favourite',
    'account_author_engagement_is_reblog_features': 'account_author_engagement_is_reblog',
    'account_author_engagement_is_reply_features': 'account_author_engagement_is_reply',
    'account_author_engagement_has_image_features': 'account_author_engagement_has_image',
    'account_author_engagement_has_gifv_features': 'account_author_engagement_has_gifv',
    'account_author_engagement_has_video_features': 'account_author_engagement_has_video',
}

spark = (
    SparkSession.builder 
    .appName("OfflineFeatureStore") 
    # .config("spark.sql.shuffle.partitions", "10") 
    .config("spark.sql.adaptive.enabled", "false")
    .config("log4j.logger.org.apache.spark.sql.execution.streaming", "INFO")
    # .config("spark.hadoop.fs.s3a.access.key", os.environ['AWS_ACCESS_KEY_ID'])
    # .config("spark.hadoop.fs.s3a.secret.key", os.environ['AWS_SECRET_ACCESS_KEY'])
    # .config("spark.hadoop.fs.s3a.endpoint", config.feast.feast_offline_store_s3_endpoint)
    # .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    # .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.jars.packages",
        #  "org.apache.hadoop:hadoop-aws:3.3.4,"
        #  "com.amazonaws:aws-java-sdk-bundle:1.11.1026,"
         "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0"
    )
    .getOrCreate()
)

# streaming queries
queries = []

for topic, fv_name in engagement_feature_topics.items():
    query = process_debezium_stream(topic, get_schema(fv_name))
    queries.append(query)

# Wait for all streams to terminate
for query in queries:
    query.awaitTermination()