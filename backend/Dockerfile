FROM public.ecr.aws/lambda/python:3.11

# Copy requirements first for better cache usage
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ${LAMBDA_TASK_ROOT}/app

# Set the CMD to your handler
CMD ["app.lambda_handler.handler"]
