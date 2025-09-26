FROM public.ecr.aws/lambda/python:3.11

# Set cache directories forsentence-transformers
ENV SENTENCE_TRANSFORMERS_HOME=${LAMBDA_TASK_ROOT}/.cache/sentence-transformers

# Copy requirements first for better cache usage
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence transformer model to the correct cache location
RUN mkdir -p ${SENTENCE_TRANSFORMERS_HOME}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY ./app ${LAMBDA_TASK_ROOT}/app

# Set the CMD to your handler
CMD ["app.lambda_handler.handler"]
