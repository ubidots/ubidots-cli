import itertools
from typing import Any

from rich.console import Console
from rich.table import Table
from typer import colors
from typer import prompt
from typer import style

from cli.commons.enums import TableColorEnum


def custom_prompt(text: str, **kwargs) -> Any:
    prompt_text = style(text, fg=colors.CYAN, bold=True)
    return prompt(prompt_text, **kwargs)


def print_colored_table(results: list[dict[str, Any]]) -> None:
    color_cycle = itertools.cycle(TableColorEnum)
    table = Table(show_header=True, header_style="bold")
    for key in results[0]:
        color = next(color_cycle).value
        table.add_column(key, style=color, header_style=color)

    for item in results:
        row = [str(item[key]) for key in item]
        table.add_row(*row)

    console = Console()
    console.print(table)
