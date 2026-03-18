from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any
from typing import Literal
from typing import TypedDict

import tomli
from pydantic import BaseModel
from pydantic import Field

from cli.commons.models import BaseYAMLDumpModel
from cli.compat import StrEnum


class AddPagePayload(TypedDict):
    name: str
    label: str


class UpdatePagePayload(TypedDict, total=False):
    name: str


class PageTypeEnum(StrEnum):
    DASHBOARD = "dashboard"


class PageProjectModel(BaseYAMLDumpModel):
    name: str
    label: str
    createdAt: str
    type: PageTypeEnum


class PageModel(BaseModel):
    id: str = ""
    label: str
    name: str


class PageProjectMetadata(BaseYAMLDumpModel):
    project: PageProjectModel
    page: PageModel


class BasePageModel(BaseModel, ABC):
    page_type: PageTypeEnum = Field(default=PageTypeEnum.DASHBOARD)
    _original_full_toml_data: dict[str, Any] = {}
    _original_toml_data: dict[str, Any] = {}

    @classmethod
    def from_toml_data(cls, toml_data: dict[str, Any]) -> "BasePageModel":
        page_data = toml_data.get("page", {})
        instance = cls(**page_data)
        instance._original_full_toml_data = toml_data
        instance._original_toml_data = page_data
        return instance

    @abstractmethod
    def get_required_toml_fields(self) -> list[str]:
        pass

    @abstractmethod
    def get_required_files(self) -> list[str]:
        pass

    @abstractmethod
    def get_required_directories(self) -> list[str]:
        pass

    def validate_structure(self) -> dict[str, Any]:
        validation_result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "manifest": self,
        }

        original_data = getattr(self, "_original_full_toml_data", {})

        for field_path in self.get_required_toml_fields():
            if not self._check_toml_path_exists(original_data, field_path):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"manifest.toml missing required path: {field_path}"
                )

        return validation_result

    def _check_toml_path_exists(self, data: dict[str, Any], path: str) -> bool:
        """Check if a dot-notation path exists in TOML data."""
        parts = path.split(".")
        current = data

        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]

        return True

    def validate_files(self, project_path: Path) -> dict[str, Any]:
        """Validate that required files exist in project directory."""
        validation_result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "manifest": self,
        }

        for file_name in self.get_required_files():
            file_path = project_path / file_name
            if not file_path.exists():
                validation_result["valid"] = False
                validation_result["errors"].append(f"Missing {file_name}")

        for dir_name in self.get_required_directories():
            dir_path = project_path / dir_name
            if not dir_path.exists() or not dir_path.is_dir():
                validation_result["valid"] = False
                validation_result["errors"].append(f"Missing {dir_name}/ directory")

        return validation_result

    def validate_complete(self, project_path: Path) -> dict[str, Any]:
        structure_result = self.validate_structure()
        if not structure_result["valid"]:
            return structure_result
        return self.validate_files(project_path)

    @classmethod
    def load_from_project(cls, project_path: Path) -> "BasePageModel":
        manifest_path = project_path / "manifest.toml"
        if not manifest_path.exists():
            msg = "Missing manifest.toml"
            raise FileNotFoundError(msg)

        try:
            with open(manifest_path, "rb") as f:
                toml_data = tomli.load(f)
        except Exception as e:
            msg = f"Invalid TOML: {e}"
            raise ValueError(msg) from e

        if "page" not in toml_data:
            msg = "manifest.toml missing [page] section"
            raise ValueError(msg)

        return cls.from_toml_data(toml_data)


class DashboardPageModel(BasePageModel):
    """Complete model for dashboard pages with all TOML fields."""

    page_type: Literal[PageTypeEnum.DASHBOARD] = PageTypeEnum.DASHBOARD

    name: str = ""
    description: str = ""
    keywords: str = ""

    is_react_enabled: bool = False
    static_paths: list[str] = Field(default_factory=list)

    js_libraries: list[dict[str, Any]] = Field(default_factory=list)
    css_libraries: list[dict[str, Any]] = Field(default_factory=list)
    link_libraries: list[dict[str, Any]] = Field(default_factory=list)
    js_thirdparty_libraries: list[dict[str, Any]] = Field(default_factory=list)
    css_thirdparty_libraries: list[dict[str, Any]] = Field(default_factory=list)
    link_thirdparty_libraries: list[dict[str, Any]] = Field(default_factory=list)

    def get_required_toml_fields(self) -> list[str]:
        """Return list of required TOML fields for dashboard pages."""
        return ["page", "page.js_libraries", "page.css_libraries"]

    def get_required_files(self) -> list[str]:
        """Return list of required files for dashboard pages."""
        return ["manifest.toml", "body.html", "script.js", "style.css"]

    def get_required_directories(self) -> list[str]:
        """Return list of required directories for dashboard pages."""
        return ["static"]


class PageModelFactory:
    """Factory for creating appropriate page models based on page type."""

    @staticmethod
    def create_page_model_from_toml(
        toml_data: dict[str, Any], page_type: PageTypeEnum
    ) -> BasePageModel:
        """Create the appropriate page model from TOML data."""
        if page_type == PageTypeEnum.DASHBOARD:
            return DashboardPageModel.from_toml_data(toml_data)
        # For future page types, add them here
        msg = f"Unsupported page type: {page_type}"
        raise ValueError(msg)

    @staticmethod
    def create_page_model_from_project(
        project_path: Path, page_type: PageTypeEnum
    ) -> BasePageModel:
        """Create page model by loading from project directory."""
        if page_type == PageTypeEnum.DASHBOARD:
            return DashboardPageModel.load_from_project(project_path)
        # For future page types, add them here
        msg = f"Unsupported page type: {page_type}"
        raise ValueError(msg)
