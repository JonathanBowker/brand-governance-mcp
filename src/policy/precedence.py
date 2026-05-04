DEFAULT_PRECEDENCE = [
    "safety",
    "regulatory",
    "legal",
    "core-brand",
    "standards",
    "applications",
    "audiences",
    "markets",
    "exceptions",
]


def precedence_rank(label: str, precedence: list[str] | None = None) -> int:
    order = precedence or DEFAULT_PRECEDENCE
    try:
        return order.index(label)
    except ValueError:
        return len(order)
