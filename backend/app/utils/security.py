import re


def sanitize_filename(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip(" .-")
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned[:120] or fallback


def redact_secret(value: str, secret: str | None, replacement: str = "[REDACTED]") -> str:
    if not secret:
        return value
    return value.replace(secret, replacement)


def redact_secrets(value: object, secrets: list[str | None], replacement: str = "[REDACTED]") -> object:
    if isinstance(value, str):
        redacted = value
        for secret in secrets:
            if secret:
                redacted = redacted.replace(secret, replacement)
        return redacted
    if isinstance(value, dict):
        return {key: redact_secrets(item, secrets, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item, secrets, replacement) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item, secrets, replacement) for item in value)
    return value
