import json
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.formatters import HumanOutputFormatter
from cli.commons.formatters import MachineOutputFormatter
from cli.commons.formatters import OutputFormatter
from cli.commons.formatters import resolve_formatter


def test_machine_emit_results_list(capsys):
    fmt = MachineOutputFormatter(command="devices list")
    fmt.emit_results([{"id": "abc", "label": "dev"}])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["command"] == "devices list"
    assert out["data"] == [{"id": "abc", "label": "dev"}]
    assert out["error"] is None
    assert out["meta"]["exit_code"] == 0
    assert "timestamp" in out["meta"]


def test_machine_emit_results_timestamp_is_iso8601(capsys):
    fmt = MachineOutputFormatter(command="test")
    fmt.emit_results([])
    out = json.loads(capsys.readouterr().out)
    datetime.strptime(out["meta"]["timestamp"], "%Y-%m-%dT%H:%M:%SZ")


def test_machine_emit_results_dict(capsys):
    fmt = MachineOutputFormatter(command="devices get")
    fmt.emit_results({"id": "abc", "label": "dev"})
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["data"] == {"id": "abc", "label": "dev"}


def test_machine_emit_success_message_only(capsys):
    fmt = MachineOutputFormatter(command="devices delete")
    with pytest.raises(typer.Exit) as exc_info:
        fmt.emit_success("Device removed successfully.")
    assert exc_info.value.exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["data"] == {"message": "Device removed successfully."}
    assert out["error"] is None


def test_machine_emit_success_with_data(capsys):
    fmt = MachineOutputFormatter(command="functions dev start")
    with pytest.raises(typer.Exit):
        fmt.emit_success("Started.", data={"label": "my_fn", "url": "http://localhost:5678"})
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["label"] == "my_fn"
    assert out["data"]["url"] == "http://localhost:5678"
    assert out["data"]["message"] == "Started."


def test_machine_emit_error(capsys):
    fmt = MachineOutputFormatter(command="devices get")
    exc = ValueError("Not found")
    with pytest.raises(typer.Exit) as exc_info:
        fmt.emit_error(exc, message="Device not found.", hint="Check the label.")
    assert exc_info.value.exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert out["data"] is None
    assert out["error"]["type"] == "ValueError"
    assert out["error"]["message"] == "Device not found."
    assert out["error"]["hint"] == "Check the label."
    assert out["meta"]["exit_code"] == 1


def test_machine_emit_error_no_hint(capsys):
    fmt = MachineOutputFormatter(command="devices get")
    with pytest.raises(typer.Exit):
        fmt.emit_error(RuntimeError("boom"))
    out = json.loads(capsys.readouterr().out)
    assert out["error"]["hint"] is None
    assert out["error"]["message"] == "boom"


def test_human_emit_results_table():
    fmt = HumanOutputFormatter(command="devices list", raw_json=False)
    with patch("cli.commons.formatters.print_colored_table") as mock_table:
        fmt.emit_results([{"id": "abc"}])
        mock_table.assert_called_once_with(results=[{"id": "abc"}])


def test_human_emit_results_dict_wrapped_in_list():
    fmt = HumanOutputFormatter(command="devices get", raw_json=False)
    with patch("cli.commons.formatters.print_colored_table") as mock_table:
        fmt.emit_results({"id": "abc"})
        mock_table.assert_called_once_with(results=[{"id": "abc"}])


def test_human_emit_results_forwards_table_kwargs():
    fmt = HumanOutputFormatter(command="devices list", raw_json=False)
    with patch("cli.commons.formatters.print_colored_table") as mock_table:
        fmt.emit_results([{"id": "abc"}], column_order=["id"])
        mock_table.assert_called_once_with(results=[{"id": "abc"}], column_order=["id"])


def test_human_emit_results_raw_json(capsys):
    fmt = HumanOutputFormatter(command="devices list", raw_json=True)
    fmt.emit_results([{"id": "abc"}])
    out = capsys.readouterr().out.strip()
    assert json.loads(out) == [{"id": "abc"}]


def test_human_emit_success(capsys):
    fmt = HumanOutputFormatter(command="devices delete", raw_json=False)
    with pytest.raises(typer.Exit) as exc_info:
        fmt.emit_success("Done.")
    assert exc_info.value.exit_code == 0
    assert "[DONE]" in capsys.readouterr().out


def test_human_emit_error(capsys):
    fmt = HumanOutputFormatter(command="devices get", raw_json=False)
    with pytest.raises(typer.Exit) as exc_info:
        fmt.emit_error(RuntimeError("boom"), message="Something failed.")
    assert exc_info.value.exit_code == 1
    assert "[ERROR]" in capsys.readouterr().out


def test_resolve_formatter_flag_takes_priority(monkeypatch):
    monkeypatch.setenv("UBIDOTS_OUTPUT_FORMAT", "table")
    mock_config = MagicMock()
    mock_config.output_format = OutputFormatFieldsEnum.TABLE
    result = resolve_formatter(flag=OutputFormatFieldsEnum.MACHINE, active_config=mock_config, command="devices list")
    assert isinstance(result, MachineOutputFormatter)


def test_resolve_formatter_env_var_beats_profile(monkeypatch):
    monkeypatch.setenv("UBIDOTS_OUTPUT_FORMAT", "machine")
    mock_config = MagicMock()
    mock_config.output_format = OutputFormatFieldsEnum.TABLE
    result = resolve_formatter(flag=None, active_config=mock_config, command="devices list")
    assert isinstance(result, MachineOutputFormatter)


def test_resolve_formatter_profile_used_when_no_flag_no_env(monkeypatch):
    monkeypatch.delenv("UBIDOTS_OUTPUT_FORMAT", raising=False)
    mock_config = MagicMock()
    mock_config.output_format = OutputFormatFieldsEnum.TABLE
    result = resolve_formatter(flag=None, active_config=mock_config, command="devices list")
    assert isinstance(result, HumanOutputFormatter)
    assert result.raw_json is False


def test_resolve_formatter_json_flag_gives_human_raw(monkeypatch):
    monkeypatch.delenv("UBIDOTS_OUTPUT_FORMAT", raising=False)
    mock_config = MagicMock()
    mock_config.output_format = OutputFormatFieldsEnum.TABLE
    result = resolve_formatter(flag=OutputFormatFieldsEnum.JSON, active_config=mock_config, command="x")
    assert isinstance(result, HumanOutputFormatter)
    assert result.raw_json is True


def test_resolve_formatter_none_active_config_falls_to_default(monkeypatch):
    monkeypatch.delenv("UBIDOTS_OUTPUT_FORMAT", raising=False)
    result = resolve_formatter(flag=None, active_config=None, command="config")
    assert isinstance(result, MachineOutputFormatter)


def test_resolve_formatter_invalid_env_var_falls_to_profile(monkeypatch):
    monkeypatch.setenv("UBIDOTS_OUTPUT_FORMAT", "invalid_value")
    mock_config = MagicMock()
    mock_config.output_format = OutputFormatFieldsEnum.MACHINE
    result = resolve_formatter(flag=None, active_config=mock_config, command="x")
    assert isinstance(result, MachineOutputFormatter)
