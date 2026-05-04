#!/usr/bin/env python
import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.utils.hash import generate_brand_key, key_hash_value, key_hint, key_lookup_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a hashed trial key file.")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-name", required=True)
    parser.add_argument("--bucket-uri", required=True)
    parser.add_argument("--index-file", required=True)
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument("--ttl", type=int, default=30)
    parser.add_argument("--out-dir", default="./dist/keys")
    parser.add_argument("--mcp-endpoint", default="https://mcp.advancedanalytica.co.uk/brand-governance")
    args = parser.parse_args()

    raw_key = generate_brand_key(args.client_id)
    now = datetime.now(UTC)
    expires = now + timedelta(days=args.ttl)
    record = {
        "clientId": args.client_id,
        "clientName": args.client_name,
        "keyHash": key_hash_value(raw_key),
        "keyHint": key_hint(raw_key),
        "tier": args.tier,
        "label": "Self-Serve Brand (Trial)" if args.tier == 1 else f"Layer {args.tier}",
        "created": now.isoformat().replace("+00:00", "Z"),
        "expires": expires.isoformat().replace("+00:00", "Z"),
        "ttlDays": args.ttl,
        "status": "active",
        "mcpEndpoint": args.mcp_endpoint,
        "bucketUri": args.bucket_uri,
        "indexFile": args.index_file,
        "accessControl": {
            "standards": True,
            "toolkits": False,
            "assetLibrary": False,
            "yamlSidecars": args.tier >= 2,
            "jsonTokens": args.tier >= 3,
            "searchIntegration": args.tier >= 3,
        },
        "watermark": args.tier == 1,
        "assetsRedacted": False,
    }
    out_dir = Path(args.out_dir) / "active"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / key_lookup_name(raw_key)
    out_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Raw key, show once only: {raw_key}")
    print(f"Key file: {out_file}")


if __name__ == "__main__":
    main()
