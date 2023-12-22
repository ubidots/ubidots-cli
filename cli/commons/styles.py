from enum import Enum
from typing import Any

from typer import colors
from typer import prompt
from typer import style


class StatusColors(Enum):
    SUCCESS = colors.GREEN
    FAILED = colors.RED
    DEFAULT = colors.WHITE
    WARNING = colors.YELLOW


def custom_prompt(text: str, **kwargs) -> Any:
    prompt_text = style(text, fg=colors.CYAN, bold=True)
    return prompt(prompt_text, **kwargs)
