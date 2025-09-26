# app/lambda_handler.py
import os, sys, logging


def _configure_logging():
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        for h in root.handlers:
            h.setLevel(level)
            h.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
            )
    else:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(level)
        sh.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        )
        root.addHandler(sh)


_configure_logging()

from mangum import Mangum
from app.main import app as fastapi_app

handler = Mangum(fastapi_app, lifespan="auto")
