
def parse_accept_language(accept_language: str) -> str | None:
    """
    Parse the Accept-Language header and return the highest-priority language code.
    """
    
    if not accept_language:
        return None

    # Split by comma and sort by quality value (q=)
    languages = accept_language.split(",")
    parsed = []

    for lang in languages:
        parts = lang.strip().split(";")
        code = parts[0]
        q = 1.0  # default quality
        if len(parts) == 2 and parts[1].startswith("q="):
            try:
                q = float(parts[1][2:])
            except ValueError:
                pass
        parsed.append((code, q))

    # Sort by quality descending
    parsed.sort(key=lambda x: x[1], reverse=True)

    return parsed[0][0].split('-')[0] if parsed else None
