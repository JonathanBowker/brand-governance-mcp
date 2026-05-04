import hashlib
import secrets
import string


def sha256_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def key_hash_value(api_key: str) -> str:
    return f"sha256:{sha256_key(api_key)}"


def key_lookup_name(api_key: str) -> str:
    return f"sha256_{sha256_key(api_key)}.json"


def generate_brand_key(client_id: str, length: int = 24) -> str:
    alphabet = string.ascii_lowercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"sk-brand-{client_id}-{token}"


def key_hint(api_key: str) -> str:
    return f"...{api_key[-4:]}" if len(api_key) >= 4 else "..."
