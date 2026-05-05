"""Semantic helpers for Brand Governance Markup Language (BGML) fields."""

from src.tools.common import tokenize


def applicability_terms(sidecar: dict) -> set[str]:
    """Collect applicability terms used to route and score standards answers."""
    applicability = sidecar.get("applicability") or {}
    terms: set[str] = set()
    for field in ("relationship_types", "use_cases", "scopes", "channels", "audiences", "exceptions"):
        for value in applicability.get(field, []) or []:
            if isinstance(value, str):
                terms.add(value)
    contexts = applicability.get("contexts") or {}
    if isinstance(contexts, dict):
        for values in contexts.values():
            for value in values or []:
                if isinstance(value, str):
                    terms.add(value)
    return terms


def matching_applicability_terms(question_tokens: set[str], sidecar: dict) -> list[str]:
    """Return applicability terms whose tokens overlap the incoming question."""
    matches: list[str] = []
    for term in sorted(applicability_terms(sidecar)):
        if tokenize(term) & question_tokens:
            matches.append(term)
    return matches

