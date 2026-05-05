from pathlib import Path

import click
import typer
from lxml import etree

SCHEMAS_DIR: Path = Path(__file__).resolve().parent / "schemas"
DTD_PATH: Path = SCHEMAS_DIR / "tree_menu_v2.dtd"
DEFAULT_MENU_PATH: Path = SCHEMAS_DIR / "default_menu_v2.xml"


def _require_bundled(path: Path, label: str) -> None:
    """Raise an actionable CLI error if a bundled schema/template is missing.

    Without this guard, callers see a raw FileNotFoundError traceback when the
    package was installed without the schema files (editable install missing
    the directory, packaging regression, etc.).
    """
    if not path.exists():
        msg = (
            f"Bundled {label} not found at {path}. "
            "Try reinstalling the package: `poetry install` (dev) or "
            "`pip install --force-reinstall ubidots-cli` (release)."
        )
        raise click.ClickException(msg)


def read_bundled_dtd() -> str:
    _require_bundled(DTD_PATH, "DTD")
    return DTD_PATH.read_text(encoding="utf-8")


def read_bundled_default_menu() -> str:
    _require_bundled(DEFAULT_MENU_PATH, "default menu XML")
    return DEFAULT_MENU_PATH.read_text(encoding="utf-8")


def validate_menu_xml(xml: str) -> None:
    """Validate an Ubidots menu XML against the bundled V2 DTD.

    Raises typer.BadParameter on syntax or DTD validation errors, surfacing
    line/column information so callers can fix the source file.
    """
    _require_bundled(DTD_PATH, "DTD")

    # Defense in depth against XXE / billion-laughs / external DTD fetches —
    # the input is local files or stdin, so the parser is locked down to
    # never resolve entities or hit the network. DTD validation runs against
    # the bundled DTD loaded explicitly below.
    parser = etree.XMLParser(no_network=True, resolve_entities=False, load_dtd=False)
    try:
        root = etree.fromstring(xml.encode("utf-8"), parser=parser)
    except etree.XMLSyntaxError as e:
        msg = f"Malformed XML: {e}"
        raise typer.BadParameter(msg) from e

    with DTD_PATH.open("rb") as dtd_file:
        dtd = etree.DTD(dtd_file)

    if not dtd.validate(root):
        errors = "\n".join(
            f"  line {entry.line}, col {entry.column}: {entry.message}"
            for entry in dtd.error_log
        )
        msg = f"XML failed V2 DTD validation:\n{errors}"
        raise typer.BadParameter(msg)
