import logging
from dataclasses import dataclass
from dataclasses import field
from typing import Any

import typer

from cli.commons.enums import MessageColorEnum
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message


@dataclass
class Pipeline:
    steps: list["PipelineStep"]
    success_message: str = ""

    def _handle_success(self) -> None:
        if self.success_message:
            exit_with_success_message(self.success_message)

    def _handle_failure(self, step: "PipelineStep", exception: Exception) -> None:
        _ = step
        exit_with_error_message(exception=exception)

    def run(self, initial_data: dict[str, Any]) -> dict[str, Any]:
        data = initial_data
        for step in self.steps:
            try:
                data = step.perform_step(data)
            except Exception as error:
                self._handle_failure(step, error)
                break

        else:
            self._handle_success()
        return data


@dataclass
class PipelineStep:
    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def log(
        self,
        data: dict[str, Any],
        message: str,
        color: MessageColorEnum | None = None,
    ):
        verbose = data.get("verbose", False)
        root = data.get("root", False)
        if verbose:
            if not logging.getLogger().hasHandlers():
                logging.basicConfig(
                    level=logging.DEBUG,
                    format=f"[%(levelname)s]: {root} -> %(name)s: %(message)s",
                )
            if color:
                message = typer.style(
                    text=message,
                    fg=color,
                    bold=True,
                )

            self.logger.debug(message)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        _ = data
        error_message = "Each step must implement the execute method."
        raise NotImplementedError(error_message)

    def perform_step(self, data: dict[str, Any]) -> dict[str, Any]:
        self.log(data=data, message="(Starting OK)", color=MessageColorEnum.INFO)

        try:
            step = self.execute(data)
        except Exception as exception:
            self.log(
                data=data, message="(Finished ERROR)\n", color=MessageColorEnum.ERROR
            )
            raise exception

        self.log(data=data, message="(Finished OK)\n", color=MessageColorEnum.SUCCESS)
        return step
