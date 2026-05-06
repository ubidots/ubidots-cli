import json
from unittest import TestCase

import typer

from cli.global_properties.enums import PropertyFormatEnum
from cli.global_properties.helpers import build_add_payload
from cli.global_properties.helpers import build_update_payload
from cli.global_properties.helpers import coerce_value
from cli.global_properties.helpers import parse_scope


class TestCoerceValue(TestCase):
    def test_string_passthrough(self):
        self.assertEqual(coerce_value("hello", PropertyFormatEnum.STRING), "hello")

    def test_int_valid(self):
        self.assertEqual(coerce_value("42", PropertyFormatEnum.INT), 42)

    def test_int_invalid_raises(self):
        with self.assertRaises(typer.BadParameter):
            coerce_value("notanumber", PropertyFormatEnum.INT)

    def test_float_valid(self):
        self.assertEqual(coerce_value("3.14", PropertyFormatEnum.FLOAT), 3.14)

    def test_float_invalid_raises(self):
        with self.assertRaises(typer.BadParameter):
            coerce_value("pi", PropertyFormatEnum.FLOAT)

    def test_bool_truthy(self):
        for raw in ("true", "True", "1", "yes", "YES"):
            self.assertIs(coerce_value(raw, PropertyFormatEnum.BOOL), True)

    def test_bool_falsy(self):
        for raw in ("false", "False", "0", "no"):
            self.assertIs(coerce_value(raw, PropertyFormatEnum.BOOL), False)

    def test_bool_invalid_raises(self):
        with self.assertRaises(typer.BadParameter):
            coerce_value("maybe", PropertyFormatEnum.BOOL)

    def test_json_valid(self):
        result = coerce_value('{"a": 1}', PropertyFormatEnum.JSON)
        self.assertEqual(result, {"a": 1})

    def test_json_invalid_raises(self):
        with self.assertRaises(typer.BadParameter):
            coerce_value("{not: valid", PropertyFormatEnum.JSON)


class TestParseScope(TestCase):
    def test_empty_string(self):
        self.assertEqual(parse_scope(""), [])

    def test_single(self):
        self.assertEqual(parse_scope("functions"), ["functions"])

    def test_multiple_with_spaces(self):
        self.assertEqual(
            parse_scope("functions, pages , dashboards"),
            ["functions", "pages", "dashboards"],
        )

    def test_strips_empty_segments(self):
        self.assertEqual(parse_scope(",functions,,pages,"), ["functions", "pages"])


class TestBuildAddPayload(TestCase):
    def test_minimum(self):
        payload = build_add_payload(
            label="api_key",
            value_format=PropertyFormatEnum.STRING,
            value="abc",
            name="",
            description="",
            scope="",
            is_secret=False,
        )
        self.assertEqual(
            payload,
            {"label": "api_key", "format": "string", "value": "abc", "isSecret": False},
        )

    def test_all_fields_with_secret_and_scope(self):
        payload = build_add_payload(
            label="max_retries",
            value_format=PropertyFormatEnum.INT,
            value="5",
            name="Max Retries",
            description="Retry budget",
            scope="functions,pages",
            is_secret=True,
        )
        self.assertEqual(payload["value"], 5)
        self.assertEqual(payload["format"], "int")
        self.assertEqual(payload["scope"], ["functions", "pages"])
        self.assertTrue(payload["isSecret"])
        self.assertEqual(payload["name"], "Max Retries")
        self.assertEqual(payload["description"], "Retry budget")


class TestBuildUpdatePayload(TestCase):
    def test_no_value_omits_value_and_format(self):
        payload = build_update_payload(
            value=None,
            value_format=None,
            name="",
            description="rotated",
            scope=None,
            is_secret=None,
        )
        self.assertNotIn("value", payload)
        self.assertNotIn("format", payload)
        self.assertNotIn("isSecret", payload)
        self.assertEqual(payload["description"], "rotated")

    def test_value_without_format_raises(self):
        with self.assertRaises(typer.BadParameter):
            build_update_payload(
                value="newval",
                value_format=None,
                name="",
                description="",
                scope=None,
                is_secret=None,
            )

    def test_value_with_format_coerces(self):
        payload = build_update_payload(
            value="3.14",
            value_format=PropertyFormatEnum.FLOAT,
            name="",
            description="",
            scope=None,
            is_secret=None,
        )
        self.assertEqual(payload["value"], 3.14)
        self.assertEqual(payload["format"], "float")

    def test_clear_scope_with_empty_string(self):
        payload = build_update_payload(
            value=None,
            value_format=None,
            name="",
            description="",
            scope="",
            is_secret=None,
        )
        self.assertEqual(payload["scope"], [])

    def test_set_scope_with_values(self):
        payload = build_update_payload(
            value=None,
            value_format=None,
            name="",
            description="",
            scope="functions",
            is_secret=None,
        )
        self.assertEqual(payload["scope"], ["functions"])

    def test_toggle_secret_explicit(self):
        true_payload = build_update_payload(
            value=None,
            value_format=None,
            name="",
            description="",
            scope=None,
            is_secret=True,
        )
        self.assertIs(true_payload["isSecret"], True)
        false_payload = build_update_payload(
            value=None,
            value_format=None,
            name="",
            description="",
            scope=None,
            is_secret=False,
        )
        self.assertIs(false_payload["isSecret"], False)

    def test_json_value_payload(self):
        payload = build_update_payload(
            value=json.dumps({"a": 1}),
            value_format=PropertyFormatEnum.JSON,
            name="",
            description="",
            scope=None,
            is_secret=None,
        )
        self.assertEqual(payload["value"], {"a": 1})
