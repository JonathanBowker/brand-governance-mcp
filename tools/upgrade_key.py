#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Enable capabilities in a local key file before uploading it.")
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--tier", type=int, required=True)
    parser.add_argument("--enable", action="append", default=[])
    args = parser.parse_args()

    path = Path(args.key_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["tier"] = args.tier
    for capability in args.enable:
        data.setdefault("accessControl", {})[capability] = True
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
