from functools import wraps
from typing import Any

import pytest
from pydantic import BaseModel

from cli.settings import settings


def override_settings(**settings_overrides):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monkeypatch = pytest.MonkeyPatch()

            def apply_overrides(settings_object: BaseModel, overrides: dict[str, Any]):
                for setting, value in overrides.items():
                    if "__" in setting:
                        # Handle nested settings
                        nested_setting, nested_value = setting.split("__", 1)
                        nested_settings_object = getattr(
                            settings_object, nested_setting
                        )
                        apply_overrides(nested_settings_object, {nested_value: value})
                    else:
                        setattr(settings_object, setting, value)

            # Apply overrides to the nested settings object, not the top-level settings object
            nested_settings_object = getattr(
                settings, settings_overrides.pop("obj", None)
            )
            apply_overrides(nested_settings_object, settings_overrides)

            try:
                return func(*args, **kwargs)
            finally:
                monkeypatch.undo()

        return wrapper

    return decorator
