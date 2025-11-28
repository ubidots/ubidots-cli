"""Tests for the pages exceptions module."""

import unittest
from pathlib import Path

from cli.pages.exceptions import CurrentPlanDoesNotIncludePagesFeature
from cli.pages.exceptions import PageAlreadyExistsInCurrentDirectoryError
from cli.pages.exceptions import PageWithNameAlreadyExistsError
from cli.pages.exceptions import TemplateNotFoundError
from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError


class TestCurrentPlanDoesNotIncludePagesFeature(unittest.TestCase):
    """Test CurrentPlanDoesNotIncludePagesFeature exception."""

    def test_exception_str_message(self):
        """Test that the exception returns the correct string message."""
        exception = CurrentPlanDoesNotIncludePagesFeature()
        expected_message = (
            "The current plan does not include the 'pages' feature. "
            "Please upgrade your plan to use this feature."
        )
        self.assertEqual(str(exception), expected_message)


class TestPageAlreadyExistsInCurrentDirectoryError(unittest.TestCase):
    """Test PageAlreadyExistsInCurrentDirectoryError exception."""

    def test_exception_str_message(self):
        """Test that the exception returns the correct string message."""
        exception = PageAlreadyExistsInCurrentDirectoryError()
        expected_message = (
            "A page already exists in the current directory. "
            "Please navigate to a different directory to create a new page."
        )
        self.assertEqual(str(exception), expected_message)


class TestPageWithNameAlreadyExistsError(unittest.TestCase):
    """Test PageWithNameAlreadyExistsError exception."""

    def test_exception_init_and_str(self):
        """Test exception initialization and string representation."""
        name = "test_page"
        page_path = "/path/to/test_page"
        exception = PageWithNameAlreadyExistsError(name, page_path)

        expected_message = f"A page with name '{name}' already exists at '{page_path}'"
        self.assertEqual(str(exception), expected_message)

    def test_exception_with_different_values(self):
        """Test exception with different name and path values."""
        name = "my_dashboard"
        page_path = "/home/user/projects/my_dashboard"
        exception = PageWithNameAlreadyExistsError(name, page_path)

        expected_message = f"A page with name '{name}' already exists at '{page_path}'"
        self.assertEqual(str(exception), expected_message)


class TestTemplateNotFoundError(unittest.TestCase):
    """Test TemplateNotFoundError exception."""

    def test_exception_init_and_str(self):
        """Test exception initialization and string representation."""
        template_file = Path("/path/to/template.zip")
        page_type = "dashboard"
        exception = TemplateNotFoundError(template_file, page_type)

        self.assertEqual(exception.template_file, template_file)
        self.assertEqual(exception.page_type, page_type)

        expected_message = (
            f"Template for page type '{page_type}' not found at '{template_file}'"
        )
        self.assertEqual(str(exception), expected_message)

    def test_exception_with_different_values(self):
        """Test exception with different template file and page type."""
        template_file = Path("/templates/custom.zip")
        page_type = "custom_type"
        exception = TemplateNotFoundError(template_file, page_type)

        expected_message = (
            f"Template for page type '{page_type}' not found at '{template_file}'"
        )
        self.assertEqual(str(exception), expected_message)


class TestPageIsAlreadyRunningError(unittest.TestCase):
    """Test PageIsAlreadyRunningError exception."""

    def test_exception_init_and_str_without_url(self):
        """Test exception initialization and string representation without URL."""
        name = "test_page"
        exception = PageIsAlreadyRunningError(name)

        self.assertEqual(exception.name, name)
        self.assertEqual(exception.url, "")

        expected_message = f"Page '{name}' is already running."
        self.assertEqual(str(exception), expected_message)

    def test_exception_init_and_str_with_url(self):
        """Test exception initialization and string representation with URL."""
        name = "test_page"
        url = "http://localhost:8090/"
        exception = PageIsAlreadyRunningError(name, url)

        self.assertEqual(exception.name, name)
        self.assertEqual(exception.url, url)

        expected_message = f"Page '{name}' is already running.\n\n🌐 Page URL: {url}"
        self.assertEqual(str(exception), expected_message)

    def test_exception_with_empty_url(self):
        """Test exception with explicitly empty URL."""
        name = "test_page"
        url = ""
        exception = PageIsAlreadyRunningError(name, url)

        expected_message = f"Page '{name}' is already running."
        self.assertEqual(str(exception), expected_message)


class TestPageIsAlreadyStoppedError(unittest.TestCase):
    """Test PageIsAlreadyStoppedError exception."""

    def test_exception_init_and_str(self):
        """Test exception initialization and string representation."""
        name = "test_page"
        exception = PageIsAlreadyStoppedError(name)

        self.assertEqual(exception.name, name)

        expected_message = f"Page '{name}' is already stopped."
        self.assertEqual(str(exception), expected_message)

    def test_exception_with_different_name(self):
        """Test exception with different page name."""
        name = "my_dashboard"
        exception = PageIsAlreadyStoppedError(name)

        expected_message = f"Page '{name}' is already stopped."
        self.assertEqual(str(exception), expected_message)


if __name__ == "__main__":
    unittest.main()
