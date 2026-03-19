# kafka-aws-streaming-pipeline
A realtime streaming ETL pipeline built with Kafka and AWS using the finnhub API, containerized with docker.

This project ingests data using Finnhub's websocket API and processes it through  a medallion structure data lakehouse. Final queryable data sits within AWS S3.

---

## Architecture

![Architecture](docs/architecture.png)

---

## Stack

| Layer | Technology |
|---|---|
|Data Source|Finnhub Websocket API|
|Message Broker|Apache Kafka|
|Stream processing|PySpark structured streaming|
|Database storage|AWS S3|
|Schema Registry|AWS Glue Catalog|
|Querying|Athena|

---

## Data flow

```
Finnhub WebSocket
      ↓
Python Producer (WebSocket → Kafka)
      ↓
Kafka Topic: raw-trades  [Docker]
      ↓
PySpark Structured Streaming  [Local]
      ↓
S3 Bronze → S3 Silver → S3 Gold
      ↓
AWS Glue Catalog
      ↓
Amazon Athena

```
---

## Medallion Architecture

### Bronze
RAW data from API written to JSON files that are then transported into S3 as parquet files. No transformations done so cleanliness and data structure is more dependend on Finnhub's end. The data was relatively clean. JSON was used instead of CSV for it's implicit type handling and better support within the structured streaming ecosystem. 

### Silver
Cleaned and typed data to the best of my ability. Added constraints such as null filtering, deduplication and column renaming. Standard best practices. UNIX timestamp conversion done.

### Gold
OHLCV modelling per symbol. Limited data due to rate limiting on the free API plan so I modelled a simple 1 minute window for 3 tickers and ensured data quality and queribility.

| Column | Description |
|---|---|
| symbol | Stock ticker (AAPL, MSFT, etc.) |
| window_start | Start of the 1-minute window |
| window_end | End of the 1-minute window |
| open | First trade price in the window |
| high | Highest trade price in the window |
| low | Lowest trade price in the window |
| close | Last trade price in the window |
| volume | Total shares traded in the window |

---

### Project Structure
```
Financial-Realtime-Streaming-ETL-pipeline-with-AWS/
├── producer/
│   ├── producer.py            # Finnhub WebSocket → Kafka
│   └── requirements.txt
├── spark_streaming/
│   ├── bronze_stream.py       # Kafka → S3 Bronze
│   ├── silver_stream.py       # S3 Bronze → S3 Silver
│   └── gold_stream.py         # S3 Silver → S3 Gold (OHLCV)
├── glue/
│   └── create_tables.py       # AWS Glue Catalog table registration
├── athena/
│   └── sample_queries.sql     # Example Gold layer queries
├── docs/
│   ├── architecture.png       # Architecture diagram
│   └── athena_results.png     # Athena query results screenshot
├── docker-compose.yml
├── .env.example
└── README.md```

--- 

## Setup 

### Prerequisites

- Docker
- Python
- OpenJDK 21
- AWS API access
- Finnhub API access

Note that additional dependencies are listed in the docker requirements file. When making this project, I ran into many dependency errors that were a result of a mismatch between apache Kafka jar files and my jdk version. If you run into a problem with the apache kafka code intializing, it is probably due to one of the jars being pulled having a version mismatch with your kafka/jdk version. I personally used OpenJDK 21.

### Clone the repo 

```bash 
git clone reponame
cd (repo name)````

### Configure .env variables

In the .env files, you need to enter in your own API keys (refer to Prerequisites)

### Start docker

```bash
docker compose up -d
```

### Install dependencies

```bash
pip install -r producer/requirements.txt
pip install pyspark boto3
```

### Create buckets for S3 buckets 

```bash
aws s3 mb s3://finnhub-pipeline-bronze --region ap-southeast-1
aws s3 mb s3://finnhub-pipeline-silver --region ap-southeast-1
aws s3 mb s3://finnhub-pipeline-gold   --region ap-southeast-1
```

### initialize glue tables 

```bash
python glue/create_tables.py
```

### Execute the pipeline 

The processes must run simultaenously on 4 terminals. I suggest split screening 4 terminals in a quadro view or using tmux to handle multiple virtual terminals.

```bash
# Terminal 1
python producer/producer.py

# Terminal 2
python spark_streaming/bronze_stream.py

# Terminal 3
python spark_streaming/silver_stream.py

# Terminal 4
python spark_streaming/gold_stream.py
```

### How to query finalized gold layer

Open the AWS dashboard and search for the Athena section in the top left search bar. Create a query and on the left configuration tab, choose "finnhub_pipeline" as the database you wish to query from.

Not that your region must match the selected region you used in your API key. If your database is hosted on West Germany, for example, your AWS console must be connected to West Germany as well to find the database. 

--- 

## Results 

### Athena Gold Layer — OHLCV Query

![Athena Results](docs/athena_results.png)

OHLCV data for three tickers (GOOGL, AMZN and MSFT) computed from live data within a one minute window. The pipeline will likely fail after a very few number of valid records, this is not a limitation of the pipeline but rather a limit for free users that finnhub imposes. After a few minutes, the connection will be forcibly closed in my experience. 

If the pipeline ran fine but there is a lack of data in S3 whilst parquet files exist, then it is likely that the pipeline was executed when the market was closed.


