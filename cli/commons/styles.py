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


def print_colored_table(
    results: list[dict[str, Any]],
    sub_keys_to_show: dict[str, list[str]] | None = None,
    column_order: list[str] | None = None,
) -> None:
    if not results:
        return

    color_cycle = itertools.cycle(TableColorEnum)
    table = Table(show_header=True, header_style="bold")

    keys_to_show: list[str] = []
    sub_keys_to_show_dict = sub_keys_to_show if sub_keys_to_show is not None else {}

    for key in results[0]:
        should_show_sub_keys = key in sub_keys_to_show_dict

        if isinstance(results[0][key], dict) and should_show_sub_keys:
            keys_to_show.extend(
                f"{key}.{sub_key}" for sub_key in sub_keys_to_show_dict[key]
            )
        else:
            keys_to_show.append(key)

    ordered_keys = (
        [key for key in column_order if key in keys_to_show]
        if column_order
        else keys_to_show
    )

    for key in ordered_keys:
        color = next(color_cycle)
        table.add_column(key, style=color, header_style=color)

    for item in results:
        row = []
        for key in ordered_keys:
            if "." in key:
                main_key, sub_key = key.split(".")
                value = item.get(main_key, {}).get(sub_key, "")
            else:
                value = item.get(key, "")
            row.append(str(value))
        table.add_row(*row)

    console = Console()
    console.print(table)
