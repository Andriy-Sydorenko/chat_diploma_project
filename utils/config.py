from dotenv import load_dotenv

from utils.enums import EncryptionAlgorithms
from utils.env_parser import EnvParser
from utils.logging_config import logger
from utils.utils import generate_jwt_secret_key, get_git_branch_name

load_dotenv()

env = EnvParser()
IS_DEPLOY_BRANCH = get_git_branch_name() == "deploy"
print(f"{IS_DEPLOY_BRANCH=}")

if IS_DEPLOY_BRANCH:
    DATABASE_URL = env.str("PRODUCTION_DATABASE_URL")
else:
    DATABASE_URL = env.str("DEFAULT_DATABASE_URL")

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
