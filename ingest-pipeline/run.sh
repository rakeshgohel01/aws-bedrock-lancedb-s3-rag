#!/bin/bash

# Check if the account number is passed as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <AWS_ACCOUNT_NUMBER>"
  exit 1
fi

# Set the AWS account number
AWS_ACCOUNT_NUMBER=$1

# Set the AWS region
AWS_REGION="us-east-1"

# Repository name
REPOSITORY_NAME="lance-rag-function"

# Check if the ECR repository exists
REPO_EXISTS=$(aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $AWS_REGION --output text --query 'repositories[0].repositoryName' 2>/dev/null)

if [ -z "$REPO_EXISTS" ]; then
  echo "ECR repository $REPOSITORY_NAME does not exist. Creating..."
  aws ecr create-repository --repository-name $REPOSITORY_NAME --region $AWS_REGION
else
  echo "ECR repository $REPOSITORY_NAME already exists."
fi

# Log in to the Amazon ECR registry
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_NUMBER}.dkr.ecr.$AWS_REGION.amazonaws.com

# Build the Docker image
cd src
docker buildx build --platform linux/amd64 -t lance-rag-function .
cd ..

# Generate a unique image tag based on the current date and time
export IMAGE_TAG=$(date +%Y%m%d%H%M%S)

echo "Image Tag: $IMAGE_TAG"

# Tag the Docker image with the unique tag
IMAGE_URI="${AWS_ACCOUNT_NUMBER}.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG"
docker tag lance-rag-function:latest "$IMAGE_URI"

# Push the Docker image to the Amazon ECR repository
docker push "$IMAGE_URI"

# Build the SAM application, replacing the image tag in the template
sam build --parameter-overrides ImageTag=$IMAGE_TAG

# Deploy the SAM application
sam deploy --stack-name lancerag \
  --image-repository "$IMAGE_URI" \
  --parameter-overrides ImageTag=$IMAGE_TAG \
  --capabilities CAPABILITY_IAM