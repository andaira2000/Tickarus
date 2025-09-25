# ---------- Stage 1: build wheels ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/build

# System deps only for building wheels (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install latest pip/wheel/setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy only prod requirements first (better caching)
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /opt/wheels -r requirements.txt

# ---------- Stage 2: minimal Lambda runtime ----------
FROM public.ecr.aws/lambda/python:3.11

# Copy prebuilt wheels and install (no compilers in final image)
COPY --from=builder /opt/wheels /opt/wheels
RUN pip install --no-cache-dir /opt/wheels/* && rm -rf /opt/wheels

# Copy application code
WORKDIR /var/task
COPY ./app ./app

# If you use FastAPI in Lambda, add a small lambda handler using Mangum:
# app/lambda_handler.py should expose "handler"
#   from mangum import Mangum
#   from app.main import app
#   handler = Mangum(app)

# (Optional) Run as non-root inside Lambda image (Lambda already runs with least privilege)
# USER sbx_user1051  # Lambda images have specific users; usually not necessary

# Lambda uses CMD as handler reference
CMD ["app.lambda_handler.handler"]
