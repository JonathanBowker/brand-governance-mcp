from src.errors import AccessDeniedError, CapabilityLockedError
from src.models.key import ClientKey


def has_format_access(client: ClientKey, requested_format: str) -> bool:
    """Return whether the client can read the requested content format."""
    if requested_format == "markdown":
        return client.access_control.standards
    if requested_format == "yaml":
        return client.access_control.yaml_sidecars and client.tier >= 2
    if requested_format == "json":
        return client.access_control.json_tokens and client.tier >= 3
    return False


def require_standards(client: ClientKey) -> None:
    """Enforce that the client can access standards content."""
    if not client.access_control.standards:
        raise AccessDeniedError("Standards access is not enabled for this key.")


def require_collection_access(client: ClientKey, group: str | None) -> None:
    """Enforce collection-level access rules for indexed content groups."""
    group = group or "standards"
    if group == "standards":
        require_standards(client)
        return
    if group == "toolkits":
        if not client.access_control.toolkits:
            raise CapabilityLockedError(
                "Toolkits access is not enabled for this key.",
                details={"capability": "toolkits"},
            )
        return
    if group == "asset-library":
        if not client.access_control.asset_library:
            raise CapabilityLockedError(
                "Asset library access is not enabled for this key.",
                details={"capability": "assetLibrary"},
            )
        return
    require_standards(client)


def require_format(client: ClientKey, requested_format: str) -> None:
    """Raise a capability error when the client cannot access the requested format."""
    if requested_format == "markdown":
        require_standards(client)
        return
    if requested_format == "yaml":
        if not has_format_access(client, requested_format):
            raise CapabilityLockedError(
                "YAML governance sidecars are available in Layer 2.",
                details={"capability": "yamlSidecars", "requiresTier": 2},
            )
        return
    if requested_format == "json":
        if not has_format_access(client, requested_format):
            raise CapabilityLockedError(
                "JSON design tokens are available in Layer 3.",
                details={"capability": "jsonTokens", "requiresTier": 3},
            )
        return
    raise ValueError("Invalid format. Must be one of: markdown, yaml, json")
