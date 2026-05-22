import click
import typer.core
from typer.models import DefaultPlaceholder


def _resolve_panel(obj: object) -> str | None:
    """Return the panel string or None if unset/placeholder."""
    val = getattr(obj, "rich_help_panel", None)
    if isinstance(val, DefaultPlaceholder) or not isinstance(val, str):
        return None
    return val


def _format_options_with_panels(cmd: click.Command, ctx: click.Context, formatter: click.HelpFormatter) -> None:
    """Write options grouped by rich_help_panel as plain-text sections."""
    args: list[tuple[str, str]] = []
    panels: dict[str | None, list[tuple[str, str]]] = {}

    for param in cmd.get_params(ctx):
        record = param.get_help_record(ctx)
        if record is None:
            continue
        if param.param_type_name == "argument":
            args.append(record)
        else:
            panel = _resolve_panel(param)
            panels.setdefault(panel, []).append(record)

    if args:
        with formatter.section("Arguments"):
            formatter.write_dl(args)

    if None in panels:
        with formatter.section("Options"):
            formatter.write_dl(panels[None])

    for panel_name, opts in panels.items():
        if panel_name is not None:
            with formatter.section(panel_name):
                formatter.write_dl(opts)


def _format_commands_with_panels(cmd: click.MultiCommand, ctx: click.Context, formatter: click.HelpFormatter) -> None:
    """Write subcommands grouped by rich_help_panel as plain-text sections."""
    panels: dict[str | None, list[tuple[str, str]]] = {}

    for name in cmd.list_commands(ctx):
        sub = cmd.get_command(ctx, name)
        if sub is None or sub.hidden:
            continue
        short_help = sub.get_short_help_str(limit=100)
        panel = _resolve_panel(sub)
        panels.setdefault(panel, []).append((name, short_help))

    if None in panels:
        with formatter.section("Commands"):
            formatter.write_dl(panels[None])

    for panel_name, cmds in panels.items():
        if panel_name is not None:
            with formatter.section(panel_name):
                formatter.write_dl(cmds)


def _plain_text_help(cmd: click.Command, ctx: click.Context) -> str:
    """Render help as plain text without Rich decorations."""
    formatter = ctx.make_formatter()

    click.Command.format_usage(cmd, ctx, formatter)
    click.Command.format_help_text(cmd, ctx, formatter)
    _format_options_with_panels(cmd, ctx, formatter)

    if isinstance(cmd, click.MultiCommand):
        _format_commands_with_panels(cmd, ctx, formatter)

    click.Command.format_epilog(cmd, ctx, formatter)
    return formatter.getvalue()


def _machine_aware_get_help(self: click.Command, ctx: click.Context) -> str:
    return _plain_text_help(self, ctx)


def install_machine_help_patch() -> None:
    typer.core.TyperCommand.get_help = _machine_aware_get_help  # type: ignore[method-assign]
    typer.core.TyperGroup.get_help = _machine_aware_get_help  # type: ignore[method-assign]
