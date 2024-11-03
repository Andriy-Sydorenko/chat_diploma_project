import base64
import hashlib
import os
import subprocess

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


def generate_jwt_secret_key(random_byte_sequence_length: int = 64) -> str:
    # `length` parameter determines the length of the random byte sequence, larger number - more "randomness"
    random_bytes = os.urandom(random_byte_sequence_length)
    sha256_hash = hashlib.sha256(random_bytes).digest()
    base64_encoded_key = base64.urlsafe_b64encode(sha256_hash).rstrip(b"=")
    scrambled_key = base64.urlsafe_b64encode(hashlib.sha256(sha256_hash[::-1]).digest()).rstrip(b"=")
    combined_key = base64_encoded_key + scrambled_key
    return combined_key.decode("utf-8")


def get_git_branch_name():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


async def cleanup_blacklisted_tokens(db: AsyncSession):
    from api.models import BlacklistedToken

    query = delete(BlacklistedToken)
    await db.execute(query)
    await db.commit()
