import os

from dotenv import load_dotenv

from logging_config import logger
from utils import generate_jwt_secret_key

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
try:
    JWT_SECRET = generate_jwt_secret_key(os.getenv("JWT_SECRET_LENGTH", 64))
except TypeError:
    logger.error(
        "If you specify JWT_SECRET_LENGTH, it must be an integer! Otherwise, delete it from environment variables."
    )
    raise SystemExit
