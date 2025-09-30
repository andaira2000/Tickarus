from mangum import Mangum
from app.main import app as fastapi_app

handler = Mangum(fastapi_app, lifespan="auto")
