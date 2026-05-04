#!/usr/bin/env python
import argparse
import mimetypes
from pathlib import Path

import boto3

from src.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a brand folder to an S3-compatible bucket.")
    parser.add_argument("--brand-dir", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    brand_dir = Path(args.brand_dir)
    for path in brand_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(brand_dir).as_posix()
        key = f"{args.prefix.rstrip('/')}/{rel}".strip("/")
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        client.upload_file(str(path), args.bucket, key, ExtraArgs={"ContentType": content_type})
        print(f"uploaded s3://{args.bucket}/{key}")


if __name__ == "__main__":
    main()
