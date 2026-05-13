import logging
import re
from collections.abc import Generator
from contextlib import contextmanager

REDACTED = "[REDACTED]"
_MIN_SECRET_LEN = 8


class _SecretRegistry:
    def __init__(self) -> None:
        self._secrets: set[str] = set()
        self._pattern: re.Pattern[str] | None = None

    def add(self, value: str | None) -> None:
        if value and len(value) >= _MIN_SECRET_LEN:
            self._secrets.add(value)
            self._pattern = re.compile("|".join(re.escape(s) for s in self._secrets))

    def scrub(self, text: str) -> str:
        if not self._pattern or not text:
            return text
        return self._pattern.sub(REDACTED, text)

    def clear(self) -> None:
        self._secrets.clear()
        self._pattern = None


_registry = _SecretRegistry()


def register_secret(value: str | None) -> None:
    _registry.add(value)


def scrub(text: str) -> str:
    return _registry.scrub(text)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _registry.scrub(str(record.msg))
        if isinstance(record.args, tuple):
            record.args = tuple(_registry.scrub(str(a)) for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: _registry.scrub(str(v)) for k, v in record.args.items()}
        return True


@contextmanager
def redaction_session() -> Generator[None]:
    """Install RedactingFilter on root logger; clear registry on exit."""
    root = logging.getLogger()
    flt = RedactingFilter()
    root.addFilter(flt)
    try:
        yield
    finally:
        root.removeFilter(flt)
        _registry.clear()
