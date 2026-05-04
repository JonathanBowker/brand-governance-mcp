import re

from src.errors import NotFoundError
from src.models.bgml import BgmlIndex, IndexEntry, Standard, parse_bgml
from src.models.key import ClientKey
from src.s3 import get_object
from src.utils.s3_uri import parse_s3_uri


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9-]+", text.lower()) if len(t) > 2}


async def load_index(client: ClientKey) -> BgmlIndex:
    uri = parse_s3_uri(client.index_file)
    raw = await get_object(uri.bucket, uri.key)
    return parse_bgml(raw)


def all_entries(index: BgmlIndex) -> list[IndexEntry]:
    entries: dict[str, IndexEntry] = {}
    for standard in index.standards:
        entries[standard.id] = standard
    for group_entries in index.collections.values():
        for entry in group_entries:
            entries[entry.id] = entry
    return list(entries.values())


def _match_by_slug(entries: list[IndexEntry], content_id: str) -> IndexEntry | None:
    matches = [entry for entry in entries if entry.slug == content_id or entry.id.split("/")[-1] == content_id]
    if len(matches) == 1:
        return matches[0]
    return None


def find_entry(index: BgmlIndex, content_id: str, *, group: str | None = None) -> IndexEntry:
    entries = all_entries(index)
    if group is not None:
        entries = [entry for entry in entries if (entry.group or "standards") == group]
    for entry in entries:
        if entry.id == content_id:
            return entry
    slug_match = _match_by_slug(entries, content_id)
    if slug_match:
        return slug_match
    raise NotFoundError(
        f"Content '{content_id}' was not found in the BGML index.",
        details={"contentId": content_id, "group": group},
    )


def find_standard(index: BgmlIndex, standard_id: str) -> Standard:
    for standard in index.standards:
        if standard.id == standard_id:
            return standard
    slug_match = _match_by_slug(index.standards, standard_id)
    if isinstance(slug_match, Standard):
        return slug_match
    raise NotFoundError(
        f"Standard '{standard_id}' was not found in the BGML index.",
        details={"standardId": standard_id},
    )


def summarise_standard(standard: Standard) -> dict:
    return {
        "id": standard.id,
        "name": standard.name,
        "category": standard.category,
        "tier": standard.tier,
        "status": standard.status,
        "description": standard.description,
        "tags": standard.tags,
        "related": standard.related,
        "version": standard.version,
        "lastModified": standard.last_modified,
    }


def summarise_entry(entry: IndexEntry) -> dict:
    return {
        "id": entry.id,
        "slug": entry.slug,
        "name": entry.name,
        "group": entry.group,
        "category": entry.category,
        "tier": entry.tier,
        "status": entry.status,
        "description": entry.description,
        "tags": entry.tags,
        "related": entry.related,
        "version": entry.version,
        "lastModified": entry.last_modified,
    }


def score_entry(entry: IndexEntry, query_tokens: set[str]) -> int:
    haystack = " ".join(
        [
            entry.id,
            entry.slug or "",
            entry.name,
            entry.group or "",
            entry.category,
            entry.description,
            " ".join(entry.tags),
            " ".join(entry.key_rules),
        ]
    )
    tokens = tokenize(haystack)
    return len(tokens & query_tokens)


def best_matches(index: BgmlIndex, question: str, limit: int = 3, groups: set[str] | None = None) -> list[IndexEntry]:
    q = tokenize(question)
    if not q:
        return []
    entries = all_entries(index)
    if groups is not None:
        entries = [entry for entry in entries if (entry.group or "standards") in groups]
    scored = [(score_entry(entry, q), entry) for entry in entries]
    return [entry for score, entry in sorted(scored, key=lambda x: x[0], reverse=True) if score > 0][:limit]
