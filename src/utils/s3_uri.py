from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class S3Uri:
    bucket: str
    key: str


def parse_s3_uri(uri: str) -> S3Uri:
    if uri.startswith(("http://", "https://")):
        parsed = urlparse(uri)
        host = parsed.netloc.split(":", 1)[0]
        if host.endswith(".digitaloceanspaces.com"):
            bucket = host.split(".", 1)[0]
            return S3Uri(bucket=bucket.strip("/"), key=parsed.path.strip("/"))
        return S3Uri(bucket=uri.strip("/"), key="")
    if not uri.startswith("s3://"):
        return S3Uri(bucket=uri.strip("/"), key="")
    rest = uri[5:]
    if "/" not in rest:
        return S3Uri(bucket=rest.strip("/"), key="")
    bucket, key = rest.split("/", 1)
    return S3Uri(bucket=bucket.strip("/"), key=key.strip("/"))


def join_s3_key(prefix: str, key: str) -> str:
    prefix = (prefix or "").strip("/")
    key = (key or "").strip("/")
    if prefix and key:
        return f"{prefix}/{key}"
    return prefix or key
