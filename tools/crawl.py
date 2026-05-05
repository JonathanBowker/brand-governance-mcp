#!/usr/bin/env python
"""Placeholder CLI entrypoint for the external crawler workflow."""

import argparse


def main() -> None:
    """Print the requested crawl inputs and remind users that crawling is external."""
    parser = argparse.ArgumentParser(description="Placeholder crawler entrypoint.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print("Crawler pipeline is intentionally external to the MCP server.")
    print(f"Input URL: {args.url}")
    print(f"Output directory: {args.output}")


if __name__ == "__main__":
    main()
