import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, NoReturn

import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import exit_with_error_message, exit_with_success_message


class OutputFormatter(ABC):
    def __init__(self, command: str) -> None:
        self.command = command

    @abstractmethod
    def emit_results(self, results: list[dict] | dict, **table_kwargs: Any) -> None:
        """Render API read results (list or single object). Does not exit."""

    @abstractmethod
    def emit_success(self, message: str, data: dict | None = None) -> NoReturn:
        """Signal successful completion. Always raises typer.Exit(0)."""

    @abstractmethod
    def emit_error(self, exception: Exception, message: str = "", hint: str = "") -> NoReturn:
        """Signal failure. Always raises typer.Exit(1)."""


class MachineOutputFormatter(OutputFormatter):
    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _dump(self, envelope: dict) -> None:
        typer.echo(json.dumps(envelope))

    def emit_results(self, results: list[dict] | dict, **table_kwargs: Any) -> None:
        self._dump({
            "status": "success",
            "command": self.command,
            "data": results,
            "error": None,
            "meta": {"exit_code": 0, "timestamp": self._now()},
        })

    def emit_success(self, message: str, data: dict | None = None) -> NoReturn:
        payload: dict = {"message": message}
        if data is not None:
            payload.update(data)
        self._dump({
            "status": "success",
            "command": self.command,
            "data": payload,
            "error": None,
            "meta": {"exit_code": 0, "timestamp": self._now()},
        })
        raise typer.Exit(0)

    def emit_error(self, exception: Exception, message: str = "", hint: str = "") -> NoReturn:
        self._dump({
            "status": "error",
            "command": self.command,
            "data": None,
            "error": {
                "type": type(exception).__name__,
                "message": message or str(exception),
                "hint": hint or None,
            },
            "meta": {"exit_code": 1, "timestamp": self._now()},
        })
        raise typer.Exit(1)


class HumanOutputFormatter(OutputFormatter):
    def __init__(self, command: str, raw_json: bool = False) -> None:
        super().__init__(command)
        self.raw_json = raw_json

    def emit_results(self, results: list[dict] | dict, **table_kwargs: Any) -> None:
        if self.raw_json:
            typer.echo(json.dumps(results))
        else:
            if isinstance(results, dict):
                results = [results]
            print_colored_table(results=results, **table_kwargs)

    def emit_success(self, message: str, data: dict | None = None) -> NoReturn:
        # data is intentionally not used in human mode — it carries machine-readable result keys only
        exit_with_success_message(message)

    def emit_error(self, exception: Exception, message: str = "", hint: str = "") -> NoReturn:
        exit_with_error_message(exception=exception, message=message, hint=hint)


def resolve_formatter(
    flag: OutputFormatFieldsEnum | None,
    active_config: Any | None,
    command: str,
) -> OutputFormatter:
    """Resolve output format via priority: flag → UBIDOTS_OUTPUT_FORMAT env → profile → default (machine)."""
    effective: OutputFormatFieldsEnum | None = flag

    if effective is None:
        env_val = os.environ.get("UBIDOTS_OUTPUT_FORMAT", "")
        if env_val:
            try:
                effective = OutputFormatFieldsEnum(env_val)
            except ValueError:
                pass  # invalid env var — fall through

    if effective is None and active_config is not None:
        effective = active_config.output_format

    if effective is None:
        effective = OutputFormatFieldsEnum.get_default_format()

    if effective == OutputFormatFieldsEnum.MACHINE:
        return MachineOutputFormatter(command=command)
    if effective == OutputFormatFieldsEnum.JSON:
        return HumanOutputFormatter(command=command, raw_json=True)
    return HumanOutputFormatter(command=command, raw_json=False)
