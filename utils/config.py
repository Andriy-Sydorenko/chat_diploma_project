from dotenv import load_dotenv

from utils.enums import EncryptionAlgorithms
from utils.env_parser import EnvParser
from utils.logging_config import logger
from utils.utils import generate_jwt_secret_key

load_dotenv()

env = EnvParser()

DATABASE_URL = env.str("DATABASE_URL")

# Time should be in minutes
ACCESS_TOKEN_EXPIRATION_TIME = env.int("ACCESS_TOKEN_EXPIRATION_TIME", 60)
ENCRYPTION_ALGORITHM = EncryptionAlgorithms.HS384

try:
    JWT_SECRET = generate_jwt_secret_key(env.int("JWT_RANDOM_BYTES_LENGTH", 64))
except TypeError:
    logger.critical(
        "If you specify JWT_SECRET_LENGTH, it must be an integer! Otherwise, delete it from environment variables."
    )
    raise SystemExit
