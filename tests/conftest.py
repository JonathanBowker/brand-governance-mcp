import json
import os
from datetime import UTC, datetime, timedelta

import boto3
import pytest
from moto import mock_aws

from src.utils.hash import key_hash_value, key_lookup_name

os.environ.setdefault("AA_S3_ENDPOINT", "")
os.environ.setdefault("AA_S3_REGION", "us-east-1")
os.environ.setdefault("AA_KEYS_REGION", "us-east-1")
os.environ.setdefault("AA_S3_ACCESS_KEY", "testing")
os.environ.setdefault("AA_S3_SECRET_KEY", "testing")

VALID_KEY = "sk-brand-pwc-testvalid123456"
EXPIRED_KEY = "sk-brand-pwc-expired123456"
INVALID_STATUS_KEY = "sk-brand-pwc-invalid123456"
TOOLKIT_KEY = "sk-brand-pwc-toolkits123456"
JSON_KEY = "sk-brand-pwc-json123456"
KEYS_BUCKET = "aa-keys"
BRAND_BUCKET = "aa-brand-pwc-trial"


def bgml_index() -> dict:
    return {
        "bgml": {
            "version": "1.0",
            "schema": "https://brandsemantics.com/schema/bgml/1.0",
            "meta": {"brand": "PwC", "layer": 1},
            "precedence": ["safety", "regulatory", "legal", "core-brand", "standards", "exceptions"],
            "standards": [
                {
                    "id": "logo",
                    "category": "visual",
                    "tier": "standards",
                    "status": "active",
                    "name": "Logo",
                    "description": "PwC logo standards. Clear space is measured by the height of the lowercase c in the wordmark.",
                    "files": {
                        "markdown": "standards/logo/page.md",
                        "yaml": "standards/logo/page.yaml",
                        "json": "standards/logo/page.json",
                        "images": {"path": "standards/logo/images/", "count": 1},
                    },
                    "keyRules": ["Never separate wordmark from Momentum Mark", "Minimum size is 48px digital"],
                    "related": ["colour"],
                    "tags": ["visual", "logo"],
                    "version": "2026.1",
                    "lastModified": "2026-05-04",
                },
                {
                    "id": "colour",
                    "category": "visual",
                    "tier": "standards",
                    "status": "active",
                    "name": "Colour",
                    "description": "Core colour is orange #FD5108 with white and black.",
                    "files": {"markdown": "standards/colour/page.md", "yaml": "standards/colour/page.yaml", "json": None},
                    "keyRules": ["Lead with orange", "Do not use orange as full background fill"],
                    "related": ["logo"],
                    "tags": ["visual", "colour"],
                    "version": "2026.1",
                    "lastModified": "2026-05-04",
                },
                {
                    "id": "data-visualisation",
                    "category": "visual",
                    "tier": "standards",
                    "status": "active",
                    "name": "Data Visualisation",
                    "description": "Guidance for charts, tables, palettes, and level-based data visualisation use.",
                    "files": {
                        "markdown": "standards/data-visualisation/page.md",
                        "yaml": "standards/data-visualisation/page.yaml",
                        "json": "standards/data-visualisation/page.json",
                        "images": {"path": "standards/data-visualisation/images/", "count": 0},
                    },
                    "keyRules": ["Lead with orange in data visualisations", "Use level-based palette guidance"],
                    "related": ["colour", "typography"],
                    "tags": ["visual", "charts", "tables", "level_1", "level_2"],
                    "version": "2026.1",
                    "lastModified": "2026-05-05",
                },
            ],
            "collections": {
                "standards": [],
                "toolkits": [
                    {
                        "id": "toolkits/social-media",
                        "slug": "social-media",
                        "group": "toolkits",
                        "category": "social-media",
                        "status": "active",
                        "name": "Social Media Toolkit",
                        "description": "Social media toolkit guidance for brand applications.",
                        "files": {
                            "markdown": "toolkits/social-media/page.md",
                            "yaml": "toolkits/social-media/page.yaml",
                            "json": "toolkits/social-media/page.json",
                            "images": {"path": "toolkits/social-media/images/", "count": 1},
                        },
                        "keyRules": ["Use approved branded templates for social content"],
                        "related": ["logo", "colour"],
                        "tags": ["toolkits", "social-media"],
                        "version": "2026.1",
                        "lastModified": "2026-05-04",
                    }
                ],
            },
        }
    }


def key_record(
    raw_key: str,
    *,
    tier: int = 1,
    expired: bool = False,
    status: str = "active",
    toolkits: bool = False,
    asset_library: bool = False,
    yaml_sidecars: bool = False,
    json_tokens: bool = False,
) -> dict:
    now = datetime.now(UTC)
    expires = now - timedelta(days=1) if expired else now + timedelta(days=30)
    return {
        "clientId": "pwc",
        "clientName": "PricewaterhouseCoopers",
        "keyHash": key_hash_value(raw_key),
        "keyHint": f"...{raw_key[-4:]}",
        "tier": tier,
        "created": now.isoformat(),
        "expires": expires.isoformat(),
        "ttlDays": 30,
        "status": status,
        "mcpEndpoint": "https://mcp.advancedanalytica.co.uk/brand-governance",
        "bucketUri": f"s3://{BRAND_BUCKET}/",
        "indexFile": f"s3://{BRAND_BUCKET}/bgml-index.json",
        "accessControl": {
            "standards": True,
            "toolkits": toolkits,
            "assetLibrary": asset_library,
            "yamlSidecars": yaml_sidecars,
            "jsonTokens": json_tokens,
            "searchIntegration": False,
        },
        "watermark": True,
        "assetsRedacted": False,
    }


@pytest.fixture()
def s3_env(monkeypatch):
    monkeypatch.setenv("AA_S3_ENDPOINT", "")
    monkeypatch.setenv("AA_S3_REGION", "us-east-1")
    monkeypatch.setenv("AA_KEYS_REGION", "us-east-1")
    monkeypatch.setenv("AA_S3_ACCESS_KEY", "testing")
    monkeypatch.setenv("AA_S3_SECRET_KEY", "testing")
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=KEYS_BUCKET)
        s3.create_bucket(Bucket=BRAND_BUCKET)
        s3.put_object(Bucket=BRAND_BUCKET, Key="bgml-index.json", Body=json.dumps(bgml_index()).encode("utf-8"))
        s3.put_object(Bucket=BRAND_BUCKET, Key="standards/logo/page.md", Body=b"# Logo\nClear space uses the lowercase c.")
        s3.put_object(Bucket=BRAND_BUCKET, Key="standards/logo/page.yaml", Body=b"standard_id: logo")
        s3.put_object(Bucket=BRAND_BUCKET, Key="standards/logo/page.json", Body=b"{\"standardId\": \"logo\"}")
        s3.put_object(Bucket=BRAND_BUCKET, Key="standards/logo/images/logo.png", Body=b"fake")
        s3.put_object(
            Bucket=BRAND_BUCKET,
            Key="standards/logo/images/manifest.json",
            Body=json.dumps(
                {
                    "version": "1.0",
                    "standardId": "logo",
                    "assets": [
                        {
                            "filename": "logo.png",
                            "title": "Primary logo example",
                            "description": "Logo example",
                            "usage": "primary_logo",
                            "assetType": "logo_variant",
                            "variant": "full_lockup",
                            "colourway": "colour_positive",
                            "approvedBackgrounds": ["white", "light_gradient", "light_photography"],
                            "approvedUseCases": ["brand_identity", "corporate_communications"],
                            "minSize": {"digitalPx": 48, "printInches": 0.375},
                            "clearspaceRule": "Height of the lowercase c in the wordmark.",
                            "tags": ["logo", "primary", "positive"],
                            "priority": 1,
                            "role": "approved_variant",
                        }
                    ],
                }
            ).encode("utf-8"),
        )
        s3.put_object(Bucket=BRAND_BUCKET, Key="standards/colour/page.md", Body=b"# Colour\nLead with orange.")
        s3.put_object(
            Bucket=BRAND_BUCKET,
            Key="standards/data-visualisation/page.md",
            Body=(
                b"# Data Visualisation\n"
                b"Level 1 uses solid orange and grey tints for everyday practitioner charts.\n"
                b"Level 2 may use gradients for designer-led applications."
            ),
        )
        s3.put_object(Bucket=BRAND_BUCKET, Key="standards/data-visualisation/page.yaml", Body=b"standard_id: data-visualisation")
        s3.put_object(
            Bucket=BRAND_BUCKET,
            Key="standards/data-visualisation/page.json",
            Body=json.dumps(
                {
                    "standard": {
                        "id": "standard.data_visualisation",
                        "title": "Data Visualisation",
                        "category": "visual",
                        "status": "active",
                        "version": "2026",
                    },
                    "bgml": {
                        "canonical_id": "pwc.brand.standard.data_visualisation",
                        "related_standards": ["standard.colour", "standard.typography"],
                    },
                    "applicability": {
                        "use_cases": ["charts", "tables"],
                        "scopes": ["all_data_visualisations", "tables", "gradients"],
                        "contexts": {"levels": ["level_1", "level_2"]},
                    },
                    "mcp": {
                        "return_format": "json",
                        "content_format": "markdown",
                        "retrieval_tags": ["data_visualisation", "level_1", "level_2", "charts", "tables"],
                        "response_groups": ["summary", "key_requirements", "level_1", "level_2", "rules", "restrictions", "tokens"],
                    },
                    "rules": [
                        {
                            "id": "rule.data_visualisation.lead_with_orange",
                            "severity": "required",
                            "statement": "Lead with orange in all data visualisations.",
                            "applies_to": ["all_data_visualisations"],
                            "source_section": "Key points",
                        }
                    ],
                    "restrictions": [
                        {
                            "id": "restriction.data_visualisation.no_gradients_level_1",
                            "severity": "prohibited",
                            "statement": "Do not use gradients in level_1 applications.",
                            "applies_to": ["level_1"],
                            "source_section": "Level 1",
                        }
                    ],
                    "tokens": [
                        {
                            "id": "token.data_visualisation.level_1_palette",
                            "token_group": "colour_palettes",
                            "name": "Level 1 palette",
                            "type": "palette",
                            "values": {
                                "colours": [
                                    "core_orange",
                                    "orange_400",
                                    "orange_300",
                                    "grey_500",
                                    "grey_300",
                                ]
                            },
                            "usage": ["Use solid orange and grey tints for level_1 charts."],
                            "restrictions": ["Do not use gradients in level_1 applications."],
                            "applies_to": ["level_1"],
                        }
                    ],
                    "examples": [
                        {
                            "id": "example.data_visualisation.level_1_charts",
                            "type": "chart_examples",
                            "description": "Level 1 bar charts and tables for everyday practitioner use.",
                            "applies_to": ["level_1"],
                            "source_section": "Level 1",
                        }
                    ],
                }
            ).encode("utf-8"),
        )
        s3.put_object(Bucket=BRAND_BUCKET, Key="toolkits/social-media/page.md", Body=b"# Social Media Toolkit\nUse approved branded templates.")
        s3.put_object(Bucket=BRAND_BUCKET, Key="toolkits/social-media/page.yaml", Body=b"toolkit_id: social-media")
        s3.put_object(Bucket=BRAND_BUCKET, Key="toolkits/social-media/page.json", Body=b"{\"contentId\": \"toolkits/social-media\"}")
        s3.put_object(Bucket=BRAND_BUCKET, Key="toolkits/social-media/images/social.png", Body=b"fake")
        s3.put_object(Bucket=BRAND_BUCKET, Key="toolkits/social-media/images/manifest.json", Body=json.dumps([{"filename": "social.png", "description": "Social toolkit example"}]).encode("utf-8"))

        valid_name = f"active/{key_lookup_name(VALID_KEY)}"
        s3.put_object(Bucket=KEYS_BUCKET, Key=valid_name, Body=json.dumps(key_record(VALID_KEY)).encode("utf-8"))
        toolkit_name = f"active/{key_lookup_name(TOOLKIT_KEY)}"
        s3.put_object(Bucket=KEYS_BUCKET, Key=toolkit_name, Body=json.dumps(key_record(TOOLKIT_KEY, toolkits=True, yaml_sidecars=True)).encode("utf-8"))
        json_name = f"active/{key_lookup_name(JSON_KEY)}"
        s3.put_object(
            Bucket=KEYS_BUCKET,
            Key=json_name,
            Body=json.dumps(key_record(JSON_KEY, tier=3, json_tokens=True)).encode("utf-8"),
        )
        expired_name = f"active/{key_lookup_name(EXPIRED_KEY)}"
        s3.put_object(Bucket=KEYS_BUCKET, Key=expired_name, Body=json.dumps(key_record(EXPIRED_KEY, expired=True)).encode("utf-8"))
        invalid_name = f"active/{key_lookup_name(INVALID_STATUS_KEY)}"
        s3.put_object(Bucket=KEYS_BUCKET, Key=invalid_name, Body=json.dumps(key_record(INVALID_STATUS_KEY, status="revoked")).encode("utf-8"))
        yield
