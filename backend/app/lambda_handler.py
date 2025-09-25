# app/lambda_handler.py

from mangum import Mangum
from app.main import app as fastapi_app

# If you're behind API Gateway at a stage (e.g., /prod), you can pass base_path="prod".
# handler = Mangum(fastapi_app, lifespan="auto", base_path="prod")
handler = Mangum(fastapi_app, lifespan="auto")

# (Optional) If you ever prefer the classic function-style entrypoint:
# def lambda_handler(event, context):
#     return handler(event, context)
