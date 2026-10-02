"""Secret redaction for every line this system prints or stores."""
import os, re

_SENSITIVE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|COOKIE)", re.I)
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+")


def secret_values():
    return [v for k, v in os.environ.items() if _SENSITIVE.search(k) and v and len(v) >= 8]


def redact(text) -> str:
    s = str(text)
    for v in secret_values():
        s = s.replace(v, "***REDACTED***")
    return _BEARER.sub(r"\1***REDACTED***", s)
