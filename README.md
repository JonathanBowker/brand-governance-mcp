# Brand Governance MCP Server

Advanced Analytica Brand-First AI Governance Platform.

This repository contains a Python FastMCP server that exposes brand governance content to MCP-compatible clients such as Claude, ChatGPT, and custom agents. It validates client API keys, gates access by commercial layer, reads brand data from DigitalOcean Spaces, and returns structured JSON responses for every tool.

## What it does

- Validates API keys using SHA-256 key hashes stored in AWS S3.
- Serves Layer 1 brand content from Markdown and BGML indexes stored in DigitalOcean Spaces.
- Gates Layer 2 YAML sidecars and Layer 3 JSON tokens behind access flags.
- Surfaces standards, toolkits, asset-library, digital, and other indexed collections through MCP.
- Lists standards, content, rules, images, and trial status.
- Generates presigned image URLs with one-hour expiry by default.
- Provides a Layer 1 `brand_answer_question` tool using indexed metadata and Markdown excerpts across permitted collections.
- Runs locally or on DigitalOcean App Platform.

## Data contract

Each indexed content folder follows this pattern:

```text
standards/logo/
  page.md
  page.yaml
  page.json
  images/
    manifest.json
```

Layer behavior:

| File | Layer | Purpose |
|---|---:|---|
| `page.md` | 1 | Narrative standard, examples, dos and donts |
| `page.yaml` | 2 | Brando governance sidecar, precedence, validation and AI controls |
| `page.json` | 3 | Compiled design-system tokens and API-ready objects |
| `images/` | 1+ | Reference assets and screenshots |

The BGML index can contain both:

- `bgml.standards`: the core standards collection
- `bgml.collections`: additional indexed groups such as `toolkits`, `asset-library`, `digital`, `resources`, and other brand content families

## MCP tools

| Tool | Layer | Description |
|---|---:|---|
| `brand_get_index` | 1 | Return the BGML index for the client brand |
| `brand_list_standards` | 1 | List available standards with summaries |
| `brand_get_standard` | 1/2/3 | Fetch Markdown, YAML, or JSON for one standard, gated by tier |
| `brand_list_content` | 1/2/3 | List indexed content across standards, toolkits, asset-library, digital, and other collections |
| `brand_get_content` | 1/2/3 | Fetch Markdown, YAML, or JSON for one indexed content entry, gated by tier and capability |
| `brand_get_rules` | 1 | Return indexed key rules for one standard |
| `brand_get_image_list` | 1 | Return images for a standard as presigned URLs |
| `brand_check_access` | 1 | Return entitlement and expiry state |
| `brand_answer_question` | 1 | Answer from BGML metadata and Markdown excerpts across permitted collections |

Future tools can be added for governed validation, conflict resolution, token export, and semantic search.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.server
```

By default, the server expects AWS S3 credentials for key lookup and DigitalOcean Spaces credentials for brand data in `.env`.

## Environment variables

```bash
AA_S3_ENDPOINT=https://brand-store.lon1.digitaloceanspaces.com
AA_S3_REGION=lon1
AA_S3_ACCESS_KEY=your_spaces_access_key
AA_S3_SECRET_KEY=your_spaces_secret_key
AA_KEYS_BUCKET=aa-keys
AA_KEYS_PROFILE=SchemaStreamCDNDeploy
AA_MCP_HOST=0.0.0.0
AA_MCP_PORT=8000
AA_MCP_PATH=/mcp/brand-governance
AA_MCP_TRANSPORT=http
AA_LOG_LEVEL=INFO
AA_PRESIGN_EXPIRY=3600
```

## Key lookup model

The server does not store or look up raw keys. It hashes the key supplied by the client and loads the matching entitlement record from AWS S3:

```text
aa-keys/
  active/
    sha256_<hash>.json
  expired/
    sha256_<hash>.json
  clients/
    pwc/
      latest.json
```

A valid key file contains `keyHash`, not `key`.

Only API key files and their TTL/expiry state live in AWS S3. All brand data files, including the BGML index, Markdown pages, YAML sidecars, JSON tokens, and images, live in DigitalOcean Spaces.
The `indexFile` field may point at a Spaces object URL such as `https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/page-index.json`.

```json
{
  "clientId": "pwc",
  "clientName": "PricewaterhouseCoopers",
  "keyHash": "sha256:...",
  "keyHint": "...p5w4",
  "tier": 1,
  "created": "2026-05-04T09:00:00Z",
  "expires": "2026-06-03T09:00:00Z",
  "status": "active",
  "mcpEndpoint": "https://advancedanalytica.co.uk/mcp/brand-governance",
  "bucketUri": "s3://aa-brand-pwc-trial/",
  "indexFile": "s3://aa-brand-pwc-trial/bgml-index.json",
  "accessControl": {
    "standards": true,
    "toolkits": false,
    "assetLibrary": false,
    "yamlSidecars": false,
    "jsonTokens": false,
    "searchIntegration": false
  },
  "watermark": true,
  "assetsRedacted": false
}
```

## Creating a trial key

```bash
python tools/create_key.py \
  --client-id pwc \
  --client-name "PricewaterhouseCoopers" \
  --bucket-uri s3://aa-brand-pwc-trial/ \
  --index-file s3://aa-brand-pwc-trial/bgml-index.json \
  --ttl 30
```

The script prints the raw key once and writes a key file containing only the hash.

## Uploading a brand dataset

```bash
python tools/upload.py --brand-dir ./brands/pwc --client-id pwc --bucket aa-brand-pwc-trial
```

## Running tests

```bash
pytest tests/
```

Tests use `moto` to mock AWS S3 for key lookup. They do not hit live AWS S3 or DigitalOcean Spaces.

## Deploying to DigitalOcean App Platform

This repo includes an App Platform spec at [.do/app.yaml](/Users/jbb/Projects/dev/brand-governance-mcp/.do/app.yaml:1) for running the MCP as a small web service under:

```text
/mcp/brand-governance
```

The intended shared app hostname is:

```text
https://advancedanalytica.co.uk/mcp/brand-governance
```

Direct browser access to this route is expected to return an MCP protocol error such as `406 Not Acceptable` or a session-related `400` response. Use an MCP client such as Claude Desktop or a FastMCP client for real tool calls.

The spec is sized for a small managed service:

- `instance_size_slug: basic-xxs`
- `instance_count: 1`
- service route with `preserve_path_prefix: true`

Before applying it to an existing app, set the run-time secrets in App Platform:

- `AA_KEYS_ACCESS_KEY`
- `AA_KEYS_SECRET_KEY`
- `AA_KEYS_SESSION_TOKEN` if your AWS credentials are temporary
- `DO_SPACES_KEY`
- `DO_SPACES_SECRET`

Then update the existing app with `doctl`:

```bash
doctl apps update <app-id> --spec .do/app.yaml
```

If the existing app already has other components, merge the `brand-governance-mcp` service into that app's full spec rather than replacing the entire spec blindly.

For the current shared Advanced Analytica app, a merged full spec is included at:

- [.do/advancedanalytica-co-uk.merged.yaml](/Users/jbb/Projects/dev/brand-governance-mcp/.do/advancedanalytica-co-uk.merged.yaml:1)

That merged spec preserves:

- the existing `web` static site
- the existing `lead-api` function mounted at `/api`
- the new `brand-governance-mcp` service mounted at `/mcp/brand-governance`

Before applying the merged spec, replace:

- the MCP repo `repo_clone_url` and branch if needed
- `AA_KEYS_ACCESS_KEY`
- `AA_KEYS_SECRET_KEY`
- `AA_KEYS_SESSION_TOKEN` if required
- `DO_SPACES_KEY`
- `DO_SPACES_SECRET`

Apply it to the existing app:

```bash
doctl apps update be8a36e2-3af3-470c-b72a-7e567c73096f --spec .do/advancedanalytica-co-uk.merged.yaml
```

## Connecting Claude Desktop

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "brand-governance": {
      "url": "https://advancedanalytica.co.uk/mcp/brand-governance",
      "headers": {
        "X-Brand-Key": "sk-brand-pwc-redacted"
      }
    }
  }
}
```

## Connecting OpenAI / ChatGPT

Use OpenAI's Responses API remote MCP configuration with a Streamable HTTP/SSE-compatible MCP endpoint. Pass the brand key through the remote MCP authorization/header configuration supported in your client environment.

## Security rules

- Never store raw API keys server-side.
- Never expose one client's bucket to another client.
- Never return raw S3 errors to the client.
- Never expose YAML sidecars to Layer 1 keys.
- Never expose JSON tokens to Layer 1 or Layer 2 keys.
- Presigned image URLs expire after one hour by default.
- Trial keys and trial buckets can be removed using lifecycle policies.

## License and IP

The Brando Schema, BGML format, and Brand-First AI Governance methodology are proprietary to Advanced Analytica unless explicitly published under a separate license.
