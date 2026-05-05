# AGENTS.md - Brand Governance MCP Server

This file is read by AI coding agents working on this repository. Follow every instruction here exactly. Do not deviate without explicit human instruction.

## What this repo is

A Python FastMCP server that:

1. Validates client API keys against AWS S3 key files with TTL expiry.
2. Serves structured brand governance data from DigitalOcean Spaces buckets.
3. Exposes brand data to LLMs via Model Context Protocol tools.
4. Runs on DigitalOcean App Platform.

## Stack

| Layer | Technology | Notes |
|---|---|---|
| MCP framework | FastMCP | Use FastMCP decorators, not raw MCP SDK |
| Web server | Uvicorn/FastMCP HTTP transport | Keep server startup in `src/server.py` |
| S3 client | boto3 via async wrappers | Use AWS S3 for key files and TTL state only |
| Spaces client | boto3 via async wrappers | Use DigitalOcean Spaces for all brand data files |
| Validation | Pydantic v2 | Use models for inputs and outputs |
| Config | python-dotenv + pydantic-settings | All secrets via env vars |
| Tests | pytest + moto | No live S3 in unit tests |

## Coding rules

### Always

- Use `async def` for tool handlers and S3 wrapper functions.
- Use Pydantic models for structured inputs and outputs.
- Use `src/s3.py` for every S3 operation.
- Use `src/config.py` as the only configuration source.
- Return structured JSON from all tools.
- Log every key validation attempt with clientId where known and timestamp.
- Handle key not found separately from invalid or access-denied cases.
- Use camelCase aliases in API-facing Pydantic models.
- Add clear docstrings to Python modules, public functions, tool handlers, and non-obvious helper functions by default.
- Keep docstrings concise and practical: explain purpose, important behavior, inputs, outputs, and fallback rules where they are not obvious from the signature.
- Check capability gates before reading protected files.
- Treat AWS S3 as the key store only; keep all brand content reads and writes on DigitalOcean Spaces.

### Never

- Never hardcode AWS or Spaces credentials.
- Never store raw API keys server-side.
- Never return raw S3 errors to clients.
- Never allow one client to access another client's bucket.
- Never skip key validation.
- Never call admin CLI scripts from tool handlers.
- Never invent standard IDs, file paths, image filenames, tokens, or rules.

## Key lookup

The server receives only an API key. It must hash the key and look up this object in AWS S3:

```text
aa-keys/active/sha256_<hash>.json
```

If not found, check:

```text
aa-keys/expired/sha256_<hash>.json
```

Store `keyHash`, not `key`, in key files.

All other brand data files, including the BGML index, Markdown, YAML, JSON, image manifests, and image assets, are stored in DigitalOcean Spaces. Do not place brand data in AWS S3.

## File structure rules

```text
src/
  server.py
  auth.py
  s3.py
  config.py
  errors.py
  prompts/
  resources/
  schema/
  templates/
  workflows/
  tools/
  models/
  policy/
  utils/
```

Do not create new top-level code folders. Add new concerns under `src/`.

Use the new `src/` subdirectories with these responsibilities:

- `src/prompts/` for prompt and instruction helpers
- `src/resources/` for runtime resource loaders and resource-oriented helpers
- `src/schema/` for BGML and structured-content semantic interpretation helpers
- `src/templates/` for response-formatting helpers
- `src/workflows/` for multi-step orchestration that may be exposed through FastMCP task execution

Do not store client binary assets in the application code tree. PowerPoint, InDesign, ZIP, video, audio, and other downloadable brand assets must live in DigitalOcean Spaces inside the relevant client dataset, not under `src/` or other repo code folders.

When adding FastMCP task support:

- Keep the public MCP interface in `src/tools/`.
- Put task-capable orchestration in `src/workflows/`.
- Prefer optional task mode first unless the feature truly requires background execution.
- Keep normal synchronous tool calls working unless the human explicitly asks for task-only behavior.

## Tool list

Layer 1 tools:

- `brand_get_index`
- `brand_list_standards`
- `brand_get_standard`
- `brand_list_content`
- `brand_get_content`
- `brand_get_rules`
- `brand_get_image_list`
- `brand_check_access`
- `brand_answer_question`

Layer 2 tools to add later:

- `brand_get_governance`
- `brand_validate_usage`
- `brand_resolve_conflict`
- `brand_check_ai_permission`

Layer 3 tools to add later:

- `brand_get_tokens`
- `brand_export_tokens`
- `brand_semantic_search`
- `brand_validate_design_asset`

## Capability mapping

| Capability | Layer 1 | Layer 2 | Layer 3 |
|---|---:|---:|---:|
| Standards Markdown | yes | yes | yes |
| Images | yes | yes | yes |
| Indexed collections via `bgml.collections` | yes, gated by capability | yes | yes |
| YAML sidecars | no | yes | yes |
| JSON tokens | no | no | yes |
| Toolkits | no by default | optional | yes |
| Asset library | no by default | optional | yes |
| Digital | optional | optional | yes |
| Semantic search | no | optional | yes |
| Validation | basic guidance only | governed validation | programmatic validation |

## BGML expectations

The index may contain both:

- `bgml.standards` for core standards entries
- `bgml.collections` for broader indexed groups such as `toolkits`, `asset-library`, `digital`, `resources`, and other content families

Do not assume the MCP server is standards-only. New tools and answer flows should respect collection-level access gates before surfacing non-standard content.

## Auth module contract

`src/auth.py` must expose:

```python
async def validate_key(api_key: str) -> ClientKey: ...
class AccessDeniedError(Exception): ...
class KeyExpiredError(Exception): ...
class KeyInvalidError(Exception): ...
```

## S3 module contract

`src/s3.py` must expose:

```python
async def get_object(bucket: str, key: str) -> str: ...
async def list_objects(bucket: str, prefix: str) -> list[str]: ...
async def get_presigned_url(bucket: str, key: str, expiry_seconds: int = 3600) -> str: ...
async def object_exists(bucket: str, key: str) -> bool: ...
```

Use boto3 only through `asyncio.to_thread` or another executor wrapper.

## Error handling

Use `src/errors.py` to convert internal exceptions into structured MCP-safe JSON responses. If FastMCP global error handlers are unavailable in the installed version, each tool wrapper must call the shared error boundary.

## Testing rules

- Every tool must have a corresponding test.
- Use moto to mock S3.
- Never hit real S3 in tests.
- Test valid key, expired key, invalid key, and capability-locked cases.

## Deployment checklist

- [ ] `pytest tests/` passes.
- [ ] `python -m compileall src tools` passes.
- [ ] `.env` is ignored.
- [ ] `.env.example` documents all required variables.
- [ ] Health check endpoint/tool is available.
- [ ] No raw keys are committed.
- [ ] No hardcoded credentials are committed.

## Questions

If requirements are unclear, stop and ask before changing access control, bucket naming, key expiry behavior, or layer mapping.

Contact: jonathan@advancedanalytica.co.uk
