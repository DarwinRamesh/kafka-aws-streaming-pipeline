import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BRONZE_PATH = "s3a://finnhub-pipeline-bronze/trades/"
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "raw-trades"

#Spark init kafka s3

spark = SparkSession.builder \
    .appName("BronzeStream") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0,"
            "org.apache.hadoop:hadoop-aws:3.4.1,"
            "com.amazonaws:aws-java-sdk-bundle:1.12.262") \
    .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
    .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
    .config("spark.hadoop.fs.s3a.endpoint", "s3.amazonaws.com") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Raw schema from Finnhub
trade_schema = StructType([
    StructField("s", StringType()),   # symbol
    StructField("p", DoubleType()),   # price
    StructField("v", DoubleType()),   # volume
    StructField("t", LongType()),     # timestamp (unix ms)
    StructField("c", StringType()),   # conditions
])

raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

parsed_stream = raw_stream \
    .selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), trade_schema).alias("data")) \
    .select("data.*") \
    .withColumn("ingested_at", current_timestamp())

# trigger interval

query = parsed_stream.writeStream \
    .format("parquet") \
    .option("path", S3_BRONZE_PATH) \
    .option("checkpointLocation", "s3a://finnhub-pipeline-bronze/checkpoints/bronze/") \
    .outputMode("append") \
    .trigger(processingTime="30 seconds") \
    .start()

query.awaitTermination()




