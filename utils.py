import base64
import hashlib
import os


def generate_jwt_secret_key(length: int = 64) -> str:
    # Generate secure random bytes
    random_bytes = os.urandom(length)

    # Hash the random bytes using SHA-256
    sha256_hash = hashlib.sha256(random_bytes).digest()

    # Base64 encode the hash to make it URL-safe
    base64_encoded_key = base64.urlsafe_b64encode(sha256_hash).rstrip(b"=")

    # Add additional entropy by reversing and rehashing
    scrambled_key = base64.urlsafe_b64encode(hashlib.sha256(sha256_hash[::-1]).digest()).rstrip(b"=")

    # Combine both the base64 encoded and scrambled key
    combined_key = base64_encoded_key + scrambled_key

    # Return as a string
    return combined_key.decode("utf-8")
