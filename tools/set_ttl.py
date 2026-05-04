#!/usr/bin/env python
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Print lifecycle policy guidance for a client bucket.")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--ttl", required=True, help="Days or 'none'")
    args = parser.parse_args()
    if args.ttl == "none":
        print(f"Remove lifecycle expiry for client {args.client_id} in your S3/Spaces console or IaC.")
    else:
        print(f"Set lifecycle expiry for client {args.client_id} to {args.ttl} days in your S3/Spaces console or IaC.")


if __name__ == "__main__":
    main()
