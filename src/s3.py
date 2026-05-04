import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import settings
from src.utils.s3_uri import join_s3_key, parse_s3_uri


class S3ObjectNotFound(Exception):
    pass


class S3AccessError(Exception):
    pass


def _normalise_spaces_endpoint(endpoint_url: str | None) -> str | None:
    if not endpoint_url:
        return endpoint_url
    if "digitaloceanspaces.com" not in endpoint_url:
        return endpoint_url
    if endpoint_url.rstrip("/") == f"https://{settings.s3_region}.digitaloceanspaces.com":
        return endpoint_url
    return f"https://{settings.s3_region}.digitaloceanspaces.com"


@lru_cache
def _spaces_client():
    kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.s3_region,
        "config": Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    }
    endpoint_url = _normalise_spaces_endpoint(settings.s3_endpoint)
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    if settings.s3_access_key and settings.s3_secret_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key
        kwargs["aws_secret_access_key"] = settings.s3_secret_key
    return boto3.client(**kwargs)


@lru_cache
def _aws_client():
    kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.keys_region,
        "config": Config(signature_version="s3v4"),
    }
    if settings.keys_access_key and settings.keys_secret_key:
        kwargs["aws_access_key_id"] = settings.keys_access_key
        kwargs["aws_secret_access_key"] = settings.keys_secret_key
        if settings.keys_session_token:
            kwargs["aws_session_token"] = settings.keys_session_token
        return boto3.client(**kwargs)

    session = boto3.session.Session(profile_name=settings.keys_profile) if settings.keys_profile else boto3.session.Session()
    return session.client(**kwargs)


def _bucket_key(bucket: str, key: str = "") -> tuple[str, str]:
    parsed = parse_s3_uri(bucket)
    prefix = (parsed.key or "").strip("/")
    normalized_key = (key or "").strip("/")
    if prefix and (normalized_key == prefix or normalized_key.startswith(f"{prefix}/")):
        full_key = normalized_key
    else:
        full_key = join_s3_key(prefix, normalized_key)
    return parsed.bucket, full_key


def _read_object_sync(client, bucket: str, key: str) -> str:
    b, k = _bucket_key(bucket, key)
    try:
        response = client.get_object(Bucket=b, Key=k)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"NoSuchKey", "NoSuchBucket", "404"}:
            raise S3ObjectNotFound(f"Object not found: s3://{b}/{k}") from exc
        raise S3AccessError("Unable to read object from storage") from exc
    body = response["Body"].read()
    return body.decode("utf-8")


def _read_object_bytes_sync(client, bucket: str, key: str) -> tuple[bytes, str | None]:
    b, k = _bucket_key(bucket, key)
    try:
        response = client.get_object(Bucket=b, Key=k)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"NoSuchKey", "NoSuchBucket", "404"}:
            raise S3ObjectNotFound(f"Object not found: s3://{b}/{k}") from exc
        raise S3AccessError("Unable to read object from storage") from exc
    body = response["Body"].read()
    return body, response.get("ContentType")


async def get_object(bucket: str, key: str) -> str:
    return await asyncio.to_thread(_read_object_sync, _spaces_client(), bucket, key)


async def get_object_bytes(bucket: str, key: str) -> tuple[bytes, str | None]:
    return await asyncio.to_thread(_read_object_bytes_sync, _spaces_client(), bucket, key)


async def get_key_object(bucket: str, key: str) -> str:
    return await asyncio.to_thread(_read_object_sync, _aws_client(), bucket, key)


def _list_objects_sync(client, bucket: str, prefix: str) -> list[str]:
    b, p = _bucket_key(bucket, prefix)
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=b, Prefix=p):
            for item in page.get("Contents", []):
                keys.append(item["Key"])
    except ClientError as exc:
        raise S3AccessError("Unable to list objects from storage") from exc
    return keys


async def list_objects(bucket: str, prefix: str) -> list[str]:
    return await asyncio.to_thread(_list_objects_sync, _spaces_client(), bucket, prefix)


def _presigned_url_sync(bucket: str, key: str, expiry_seconds: int) -> str:
    b, k = _bucket_key(bucket, key)
    try:
        return _spaces_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": b, "Key": k},
            ExpiresIn=expiry_seconds,
        )
    except ClientError as exc:
        raise S3AccessError("Unable to generate image URL") from exc


async def get_presigned_url(bucket: str, key: str, expiry_seconds: int = 3600) -> str:
    return await asyncio.to_thread(_presigned_url_sync, bucket, key, expiry_seconds)


def _object_exists_sync(client, bucket: str, key: str) -> bool:
    b, k = _bucket_key(bucket, key)
    try:
        client.head_object(Bucket=b, Key=k)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NoSuchBucket"}:
            return False
        raise S3AccessError("Unable to check object existence") from exc


async def object_exists(bucket: str, key: str) -> bool:
    return await asyncio.to_thread(_object_exists_sync, _spaces_client(), bucket, key)


async def key_object_exists(bucket: str, key: str) -> bool:
    return await asyncio.to_thread(_object_exists_sync, _aws_client(), bucket, key)
