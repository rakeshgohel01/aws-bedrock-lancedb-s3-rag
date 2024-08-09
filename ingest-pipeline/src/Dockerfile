# Use the official AWS Lambda Python image
FROM public.ecr.aws/lambda/python:3.11

# Install required packages
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Command to run the Lambda function
CMD ["app.lambda_handler"]