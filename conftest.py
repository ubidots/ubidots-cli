from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_active_profile_name():
    with patch("cli.commons.endpoint._get_active_profile_name", return_value="default"):
        yield
