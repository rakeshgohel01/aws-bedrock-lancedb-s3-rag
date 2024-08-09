import json
import boto3
from loguru import logger
import os, sys, uuid
import lancedb as ldb
import pyarrow as pa
from langchain_aws import BedrockEmbeddings

logger.remove()
logger.add(sys.stdout, level=os.getenv("LOG_LEVEL", "INFO"))

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    logger.info("Starting")

    s3_client = boto3.client('s3')
    region = os.getenv("AWS_REGION", "us-east-1")
    lanceDbSrc = os.getenv("LANCEDB_STORE", "rag-lancedb")
    lanceDbTable = os.getenv("LANCEDB_TABLE", "doc-table")

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    local_file_path = '/tmp/data.json'
    try:
        s3_client.download_file(bucket, key, local_file_path)
        logger.info(f"File downloaded to {local_file_path}")
    except Exception as e:
        logger.error(f"Error downloading file from S3: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": str(e)})}

    try:
        with open(local_file_path, 'r') as f:
            documents = [
                {
                    "page_content": f"Question: {data[0]} Answer: {data[1]}",
                    "metadata": {"source": key, "author": "unknown"}
                }
                for data in map(json.loads, f)
                if isinstance(data, list) and len(data) == 2
            ]
        logger.info(f"File read successfully with {len(documents)} documents")
    except Exception as e:
        logger.error(f"Error reading downloaded file: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": str(e)})}

    logger.info("Connecting to LanceDB")
    connection = ldb.connect(f"s3://{lanceDbSrc}/embeddings")
    schema = pa.schema([
        pa.field("vector", pa.list_(pa.float32(), 1024)),
        pa.field("text", pa.string()),
        pa.field("id", pa.string()),
        pa.field("metadata", pa.struct([
            pa.field("source", pa.string()),
            pa.field("author", pa.string())
        ]))
    ])

    try:
        table = connection.open_table(lanceDbTable)
    except Exception:
        logger.info(f"Table {lanceDbTable} not found. Creating it.")
        table = connection.create_table(lanceDbTable, schema=schema)

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", region_name=region)
    texts = [doc["page_content"] for doc in documents]
    vectors = embeddings.embed_documents(texts)
    metadata_list = [doc["metadata"] for doc in documents]

    data = [
        pa.array(vectors, pa.list_(pa.float32(), 1024)),
        pa.array(texts),
        pa.array([str(uuid.uuid4()) for _ in documents]),
        pa.array(metadata_list, pa.struct([
            pa.field("source", pa.string()),
            pa.field("author", pa.string())
        ]))
    ]

    table.add(pa.Table.from_arrays(data, schema=schema))

    logger.info("Finished storing records using Amazon Bedrock Titan text embedding")
    return {"statusCode": 200, "body": json.dumps({"message": "OK"})}

def main():
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "rag-lancedb"
                    },
                    "object": {
                        "key": "data1.json"
                    }
                }
            }
        ]
    }
    context = {}
    response = lambda_handler(event, context)
    print(response)

if __name__ == "__main__":
    main()