from datetime import UTC, datetime, timedelta

from src.models.bgml import parse_bgml
from src.models.key import ClientKey
from src.utils.hash import key_hash_value


def test_client_key_camel_case_aliases():
    now = datetime.now(UTC)
    data = {
        "clientId": "pwc",
        "clientName": "PricewaterhouseCoopers",
        "keyHash": key_hash_value("abc"),
        "tier": 1,
        "created": now.isoformat(),
        "expires": (now + timedelta(days=1)).isoformat(),
        "status": "active",
        "mcpEndpoint": "https://example.com",
        "bucketUri": "s3://bucket/",
        "indexFile": "s3://bucket/bgml-index.json",
        "accessControl": {"standards": True, "toolkits": False, "assetLibrary": False, "yamlSidecars": False, "jsonTokens": False, "searchIntegration": False},
        "watermark": True,
        "assetsRedacted": False,
    }
    model = ClientKey.model_validate(data)
    assert model.client_id == "pwc"
    assert model.model_dump(by_alias=True)["clientId"] == "pwc"


def test_parse_bgml_envelope():
    raw = {"bgml": {"version": "1.0", "meta": {"brand": "PwC"}, "precedence": [], "standards": []}}
    index = parse_bgml(raw)
    assert index.meta["brand"] == "PwC"


def test_parse_bgml_collections():
    raw = {
        "bgml": {
            "version": "1.0",
            "meta": {"brand": "PwC"},
            "precedence": [],
            "standards": [],
            "collections": {
                "toolkits": [
                    {
                        "id": "toolkits/social-media",
                        "slug": "social-media",
                        "group": "toolkits",
                        "category": "social-media",
                        "status": "active",
                        "name": "Social Media Toolkit",
                        "description": "Toolkit guidance",
                        "files": {"markdown": "toolkits/social-media/page.md", "yaml": "toolkits/social-media/page.yaml", "json": None},
                    }
                ]
            },
        }
    }
    index = parse_bgml(raw)
    assert "toolkits" in index.collections
    assert index.collections["toolkits"][0].id == "toolkits/social-media"
