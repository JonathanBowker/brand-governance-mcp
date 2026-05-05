"""Tool module registry for the Brand Governance MCP server."""

from src.tools import access, answer, content, images, index, list, rules, standard

TOOL_MODULES = [index, list, standard, content, rules, access, images, answer]

__all__ = ["TOOL_MODULES"]
