import logging
from unittest import TestCase

import pytest

import cli.auth.redaction as redaction_module
from cli.auth.redaction import REDACTED
from cli.auth.redaction import RedactingFilter
from cli.auth.redaction import redaction_session
from cli.auth.redaction import register_secret
from cli.auth.redaction import scrub


@pytest.fixture(autouse=True)
def clear_registry():
    yield
    redaction_module._registry.clear()


class TestScrub(TestCase):
    def test_register_then_scrub_replaces_all_occurrences(self):
        # Setup
        register_secret("longsecret123")
        # Action
        result = scrub("x=longsecret123 y=longsecret123")
        # Expected
        self.assertEqual(result, f"x={REDACTED} y={REDACTED}")

    def test_short_value_not_registered_passthrough(self):
        # Setup
        register_secret("short")
        # Action
        result = scrub("short")
        # Expected
        self.assertEqual(result, "short")

    def test_empty_string_passthrough(self):
        # Setup
        # (none)
        # Action
        result = scrub("")
        # Expected
        self.assertEqual(result, "")

    def test_none_registration_ignored(self):
        # Setup
        register_secret(None)
        # Action
        result = scrub("anything")
        # Expected
        self.assertEqual(result, "anything")

    def test_multiple_secrets_all_scrubbed(self):
        # Setup
        secret_a = "alphasecret01"
        secret_b = "betasecret002"
        register_secret(secret_a)
        register_secret(secret_b)
        # Action
        result = scrub(f"a={secret_a} b={secret_b}")
        # Expected
        self.assertNotIn(secret_a, result)
        self.assertNotIn(secret_b, result)
        self.assertEqual(result, f"a={REDACTED} b={REDACTED}")


class TestRedactingFilter:
    def test_logging_filter_scrubs_record_msg(self, caplog):
        # Setup
        secret = "supersecret99"
        register_secret(secret)
        logger = logging.getLogger("test_msg")
        logger.addFilter(RedactingFilter())
        # Action
        with caplog.at_level(logging.INFO, logger="test_msg"):
            logger.info(secret)
        # Expected
        assert secret not in caplog.text
        assert REDACTED in caplog.text

    def test_logging_filter_scrubs_record_args(self, caplog):
        # Setup
        secret = "supersecret99"
        register_secret(secret)
        logger = logging.getLogger("test_args")
        logger.addFilter(RedactingFilter())
        # Action
        with caplog.at_level(logging.INFO, logger="test_args"):
            logger.info("got %s", secret)
        # Expected
        assert secret not in caplog.text
        assert REDACTED in caplog.text

    def test_logging_filter_scrubs_dict_args(self, caplog):
        # Setup
        secret = "supersecret99"
        register_secret(secret)
        logger = logging.getLogger("test_dict_args")
        logger.addFilter(RedactingFilter())
        # Action
        with caplog.at_level(logging.INFO, logger="test_dict_args"):
            logger.info("val: %(k)s", {"k": secret})
        # Expected
        assert secret not in caplog.text
        assert REDACTED in caplog.text


class TestRedactionSession:
    def test_session_clears_registry_on_exit(self):
        # Setup
        secret = "sessionSecret42"
        # Action
        with redaction_session():
            register_secret(secret)
            assert scrub(secret) == REDACTED
        # Expected
        assert scrub(secret) == secret

    def test_session_installs_and_removes_filter(self):
        # Setup
        root = logging.getLogger()
        filter_types_before = [type(f) for f in root.filters]
        assert RedactingFilter not in filter_types_before
        # Action
        with redaction_session():
            active_types = [type(f) for f in root.filters]
            assert RedactingFilter in active_types
        # Expected
        after_types = [type(f) for f in root.filters]
        assert RedactingFilter not in after_types
