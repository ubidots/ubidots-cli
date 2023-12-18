from functools import wraps

import pytest

from cli import settings


def mock_settings(**settings_overrides):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monkeypatch = pytest.MonkeyPatch()
            for setting, value in settings_overrides.items():
                monkeypatch.setattr(settings, setting, value)
            try:
                return func(*args, **kwargs)
            finally:
                monkeypatch.undo()

        return wrapper

    return decorator
