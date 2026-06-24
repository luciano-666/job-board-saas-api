from datetime import datetime, timezone


def current_timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.isoformat().replace("+00:00", "Z")
