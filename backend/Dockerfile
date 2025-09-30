FROM public.ecr.aws/lambda/python:3.11

ENV SENTENCE_TRANSFORMERS_HOME=${LAMBDA_TASK_ROOT}/.cache/sentence-transformers

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence transformer model to the correct cache location
RUN mkdir -p ${SENTENCE_TRANSFORMERS_HOME}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY ./app ${LAMBDA_TASK_ROOT}/app

CMD ["app.lambda_handler.handler"]
