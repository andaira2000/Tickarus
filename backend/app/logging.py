import logging
import logging.handlers
import os
import sys
from pathlib import Path


def configure_logging():
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

    root = logging.getLogger()
    root.setLevel(level)

    root.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root.addHandler(console_handler)

    try:
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)

        log_file = logs_dir / "backend.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        print(f"Logging configured: stdout + file ({log_file})")

    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")
        print("Continuing with console logging only")
