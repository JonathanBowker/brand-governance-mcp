from src.utils.s3_uri import parse_s3_uri


def test_parse_s3_uri_supports_digitalocean_spaces_https_url():
    parsed = parse_s3_uri("https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/page-index.json")
    assert parsed.bucket == "brand-store"
    assert parsed.key == "brand-pwc/page-index.json"


def test_parse_s3_uri_supports_s3_uri():
    parsed = parse_s3_uri("s3://aa-brand-pwc-trial/bgml-index.json")
    assert parsed.bucket == "aa-brand-pwc-trial"
    assert parsed.key == "bgml-index.json"
