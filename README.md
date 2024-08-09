# RAG: AWS Bedrock with LanceDB on S3

This repository contains scripts for deploying an AWS Bedrock Knowledge Base integrated with LanceDB on S3 as the vector store. This setup utilizes AWS's managed services to build a scalable retrieval-augmented generation (RAG) system, storing and retrieving vector embeddings for various use cases.

## Overview

The solution consists of the following components:

- **AWS Bedrock**: Used for generating text embeddings with models like Amazon Titan.
- **LanceDB on S3**: Serves as the vector database for storing embeddings and supports retrieval operations.
- **Amazon S3**: Acts as a storage for input data files, which should be in JSON format.

## Input Data Format

The input data files should be in JSON format with the following structure:

```json
[
  "Question text goes here",
  "Corresponding answer text goes here"
]
```

Example:
```json
[
  "What Does Medicare IME Stand For?",
  "According to the Centers for Medicare and Medicaid Services website, IME stands for Indirect Medical Education and is in regards to payment calculation adjustments for a Medicare discharge of higher cost patients receiving care from teaching hospitals relative to non-teaching hospitals."
]
```

## Prerequisites

Before deploying the solution, ensure you have the following prerequisites set up:

1. **AWS CLI**: Configure the AWS CLI with the necessary credentials. You can install it from the [AWS CLI website](https://aws.amazon.com/cli/).

2. **AWS Account**: Ensure you have access to an AWS account with the necessary permissions to create resources.

3. **SAM CLI**: Install the AWS SAM CLI to build and deploy the serverless application. You can install it from the [AWS SAM website](https://aws.amazon.com/serverless/sam/).

## Variables

Here are the key parameters used in the SAM template:

- **region**: The AWS region where the resources will be deployed. Default is `us-east-1`.
- **LANCEDB_STORE**: The S3 bucket name where data files for LanceDB will be stored. Default is `rag-lancedb`.
- **doc-table**: The name of the LanceDB table for storing vector embeddings.
- **model_id**: The ID of the foundational model used by the knowledge base. Default is `amazon.titan-embed-text-v2:0`.

## Steps for Deployment

### 1. Clone the Repository

Clone the repository to your local machine:

```bash
git clone git@github.com:yourusername/aws-bedrock-lancedb-s3.git
cd aws-bedrock-lancedb-s3
```

### 2. Deploy with run.sh

The ingest_pipeline directory contains a run.sh script that automates the build and deployment process. This script requires the AWS account number as an input parameter.

To deploy the solution, run the following command:

```bash
./ingest_pipeline/run.sh <AWS_ACCOUNT_NUMBER>
```

This will automatically build the Docker image, push it to ECR, and deploy the SAM application with the necessary parameters.

### 3. Upload Data to S3

Upload your data files to the S3 bucket created by the deployment. The supported format is .json and should follow this structure:

```json
[
  "What Does Medicare IME Stand For?",
  "According to the Centers for Medicare and Medicaid Services website, IME stands for Indirect Medical Education and is in regards to payment calculation adjustments for a Medicare discharge of higher cost patients receiving care from teaching hospitals relative to non-teaching hospitals."
]
```

# Testing

## 1. Run the Flask App

After deploying the solution and setting up the vector store, you can use the Flask app in the `retrieve-generate` folder to query the vector store.

Navigate to the `retrieve-generate` folder and run the Flask app:

```bash
cd retrieve-generate
python app.py
```
The Flask app will start running on http://0.0.0.0:5001.

## 2. Make a Query Using curl

You can test the Flask app by making a POST request to the /query endpoint. Here’s an example using curl:

```bash
curl -X POST http://0.0.0.0:5001/query \
-H "Content-Type: application/json" \
-d '{
  "query": "What does Medicare IME stand for?"
}'
```

This curl command sends a JSON payload with your query to the Flask app, which will return the response based on the vector store’s data.

# Cleanup

To destroy the resources created by SAM:

```bash
sam delete --stack-name name
```

# License

This source code is licensed under the MIT License. See the LICENSE file for details.