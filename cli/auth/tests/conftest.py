import webbrowser
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _block_real_browser_open(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_open = MagicMock(return_value=True)
    monkeypatch.setattr(webbrowser, "open", mock_open)
    return mock_open
