from dataclasses import dataclass
from typing import Any

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
                data = step.execute(data)
            except Exception as error:
                self._handle_failure(step, error)
                break

        else:
            self._handle_success()
        return data


class PipelineStep:
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        _ = data
        error_message = "Each step must implement the execute method."
        raise NotImplementedError(error_message)
