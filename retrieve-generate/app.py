import json
import os
from langchain_community.vectorstores import LanceDB
from langchain_aws import BedrockEmbeddings
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from lancedb import connect
from flask import Flask, request, Response

import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)

lanceDbSrc = os.getenv('LANCEDB_STORE', 'rag-lancedb')
lanceDbTable = os.getenv('LANCEDB_TABLE', 'doc-table')
awsRegion = os.getenv('region', 'us-east-1')

def format_documents_as_string(documents):
    logger.debug(f"Formatting {len(documents)} documents into a string")
    formatted = "\n\n".join([f"Document {i+1}:\n{doc.page_content}" for i, doc in enumerate(documents)])
    logger.debug(f"Formatted documents: {formatted[:500]}...")  # Log only the first 500 characters
    return formatted

def run_chain(query, streaming_format=None):
    logger.info(f"Running chain with query: {query}")
    logger.info(f"LanceDB Source: {lanceDbSrc}, Table: {lanceDbTable}, AWS Region: {awsRegion}")

    # Connect to LanceDB
    try:
        db = connect(f"s3://{lanceDbSrc}/embeddings",read_consistency_interval=5)
        table = db.open_table(lanceDbTable)

        logger.debug(f"Connected to LanceDB and opened table: {lanceDbTable}")
    except Exception as e:
        logger.error(f"Error connecting to LanceDB: {e}")
        raise

    # Initialize Bedrock Embeddings
    try:
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v2:0",
            region_name=awsRegion)
        logger.debug(f"Initialized Bedrock Embeddings")
    except Exception as e:
        logger.error(f"Error initializing Bedrock Embeddings:{e}")
        raise

    # Initialize LanceDB VectorStore using the table and embeddings
    try:

        vector_store = LanceDB(connection=db,
                               table_name=lanceDbTable,
                               embedding=embeddings)

        logger.debug(f"Initialized LanceDB VectorStore and Retriever")
    except Exception as e:
        logger.error(f"Error initializing LanceDB VectorStore: {e}")
        raise

    # Create prompt template
    try:
        prompt = PromptTemplate.from_template(
            "Answer the following question based only on the following context:\n"
            "{context}\n\n"
            "Question: {question}"
        )
        logger.debug(f"Created prompt template")
    except Exception as e:
        logger.error(f"Error creating prompt template: {e}")
        raise

    # Initialize LLM model
    try:
        llm_model = ChatBedrock(
            region_name=awsRegion,
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            model_kwargs=dict(temperature=0),
            streaming=False,
        )
        logger.debug(f"Initialized LLM model with model id: {llm_model}")
    except Exception as e:
        logger.error(f"Error initializing LLM model: {e}")
        raise

    try:
        retrieved_docs = vector_store.similarity_search(query)
        context = format_documents_as_string(retrieved_docs)
        prompt_text = prompt.format(context=context, question=query)
        stream = llm_model.stream(prompt_text)
        logger.info(f"Chain execution started successfully")
        return stream
    except Exception as e:
        logger.error(f"Error during chain execution: {e}")
        raise

@app.route('/query', methods=['POST'])
def query_handler():
    try:
        logger.info(f"Received query request")

        body = request.get_json()
        logger.debug(f"Request body: {body}")
        query = body.get('query')
        streaming_format = body.get('streamingFormat')

        stream = run_chain(query, streaming_format)

        def generate():
            for chunk in stream:
                chunk_str = chunk.content
                if streaming_format == 'fetch-event-source':
                    yield f"event: message\n"
                    yield f"data: {chunk_str}\n\n"
                else:
                    yield chunk_str

        return Response(generate(), content_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in query_handler: {e}")
        return json.dumps({"error": str(e)}), 500

def parse_base64(message):
    logger.debug(f"Parsing base64 message")
    return json.loads(base64.b64decode(message).decode('utf-8'))


if __name__ == "__main__":
    logger.info("Starting Flask app")
    app.run(debug=True, host='0.0.0.0', port=5001)