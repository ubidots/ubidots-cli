from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import click
import pytest
import typer

from cli.apps.validators import DEFAULT_MENU_PATH
from cli.apps.validators import DTD_PATH
from cli.apps.validators import read_bundled_default_menu
from cli.apps.validators import read_bundled_dtd
from cli.apps.validators import validate_menu_xml

FIXTURES = Path(__file__).parent / "fixtures"


class TestValidateMenuXml(TestCase):
    def test_valid_v2_xml_passes(self):
        xml = (FIXTURES / "menu_valid.xml").read_text(encoding="utf-8")
        self.assertIsNone(validate_menu_xml(xml))

    def test_malformed_xml_raises(self):
        with pytest.raises(typer.BadParameter) as ctx:
            validate_menu_xml("<not><closed>")
        self.assertIn("Malformed XML", str(ctx.value))

    def test_missing_required_attribute_raises(self):
        xml = (FIXTURES / "menu_invalid.xml").read_text(encoding="utf-8")
        with pytest.raises(typer.BadParameter) as ctx:
            validate_menu_xml(xml)
        self.assertIn("DTD", str(ctx.value))

    def test_unknown_root_element_raises(self):
        with pytest.raises(typer.BadParameter):
            validate_menu_xml("<unknown/>")


class TestReadBundledDtd(TestCase):
    def test_dtd_path_exists(self):
        self.assertTrue(DTD_PATH.exists())

    def test_dtd_content_has_tree_element(self):
        content = read_bundled_dtd()
        self.assertIn("<!ELEMENT tree", content)
        self.assertIn("asidepanel", content)


class TestBundledDefaultMenu(TestCase):
    def test_default_menu_path_exists(self):
        self.assertTrue(DEFAULT_MENU_PATH.exists())

    def test_default_menu_validates_against_dtd(self):
        validate_menu_xml(read_bundled_default_menu())

    def test_default_menu_has_no_unrendered_django_placeholders(self):
        content = read_bundled_default_menu()
        self.assertNotIn("{% trans", content)
        self.assertNotIn("{% load", content)


class TestMissingBundledFilesRaiseActionableError(TestCase):
    def test_read_bundled_dtd_raises_click_exception_when_missing(self):
        with (
            patch("cli.apps.validators.DTD_PATH", Path("/nonexistent.dtd")),
            pytest.raises(click.ClickException) as ctx,
        ):
            read_bundled_dtd()
        self.assertIn("Bundled DTD", ctx.value.message)
        self.assertIn("reinstall", ctx.value.message.lower())

    def test_read_bundled_default_menu_raises_click_exception_when_missing(self):
        with (
            patch("cli.apps.validators.DEFAULT_MENU_PATH", Path("/nonexistent.xml")),
            pytest.raises(click.ClickException) as ctx,
        ):
            read_bundled_default_menu()
        self.assertIn("default menu XML", ctx.value.message)

    def test_validate_menu_xml_raises_click_exception_when_dtd_missing(self):
        with (
            patch("cli.apps.validators.DTD_PATH", Path("/nonexistent.dtd")),
            pytest.raises(click.ClickException) as ctx,
        ):
            validate_menu_xml(
                "<tree><body><section text='x'><menu label='y'><item label='z'/></menu></section></body></tree>"
            )
        self.assertIn("Bundled DTD", ctx.value.message)
