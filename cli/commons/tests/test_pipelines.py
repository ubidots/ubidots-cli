from unittest.mock import MagicMock, patch

import pytest
import typer

from cli.commons.pipelines import Pipeline, PipelineStep


class _SuccessStep(PipelineStep):
    """Step that always succeeds and adds a key to data."""

    def execute(self, data):
        data["label"] = "my_fn"
        data["url"] = "http://localhost:5678"
        return data


class _FailingStep(PipelineStep):
    """Step that always raises."""

    def execute(self, data):
        raise RuntimeError("step failed")


def test_pipeline_success_no_formatter_calls_exit_with_success():
    """Without formatter, success path calls exit_with_success_message."""
    pipeline = Pipeline(steps=[_SuccessStep()], success_message="Done.")
    with patch("cli.commons.pipelines.exit_with_success_message") as mock_success:
        mock_success.side_effect = typer.Exit(0)
        with pytest.raises(typer.Exit):
            pipeline.run({})
        mock_success.assert_called_once_with("Done.")


def test_pipeline_failure_no_formatter_calls_exit_with_error():
    """Without formatter, error path calls exit_with_error_message."""
    pipeline = Pipeline(steps=[_FailingStep()], success_message="Done.")
    with patch("cli.commons.pipelines.exit_with_error_message") as mock_error:
        mock_error.side_effect = typer.Exit(1)
        with pytest.raises(typer.Exit):
            pipeline.run({})
        mock_error.assert_called_once()


def test_pipeline_success_with_formatter_and_success_message():
    """formatter.emit_success called with message and filtered result_keys."""
    mock_fmt = MagicMock()
    mock_fmt.emit_success.side_effect = typer.Exit(0)
    pipeline = Pipeline(
        steps=[_SuccessStep()],
        success_message="Started.",
        result_keys=["label", "url"],
        formatter=mock_fmt,
    )
    with pytest.raises(typer.Exit):
        pipeline.run({})
    mock_fmt.emit_success.assert_called_once_with(
        "Started.", data={"label": "my_fn", "url": "http://localhost:5678"}
    )


def test_pipeline_success_with_formatter_empty_success_message_does_not_emit():
    """When success_message is empty (list/get commands), formatter.emit_success is NOT called."""
    mock_fmt = MagicMock()
    pipeline = Pipeline(
        steps=[_SuccessStep()],
        success_message="",
        result_keys=[],
        formatter=mock_fmt,
    )
    pipeline.run({})
    mock_fmt.emit_success.assert_not_called()


def test_pipeline_failure_with_formatter_calls_emit_error():
    """formatter.emit_error called when a step raises."""
    mock_fmt = MagicMock()
    mock_fmt.emit_error.side_effect = typer.Exit(1)
    pipeline = Pipeline(
        steps=[_FailingStep()],
        success_message="Done.",
        formatter=mock_fmt,
    )
    with pytest.raises(typer.Exit):
        pipeline.run({})
    mock_fmt.emit_error.assert_called_once()
    exc_arg = mock_fmt.emit_error.call_args[0][0]
    assert isinstance(exc_arg, RuntimeError)


def test_pipeline_injects_formatter_into_data():
    """formatter is accessible via data['formatter'] inside pipeline steps."""
    captured = {}

    class _CaptureStep(PipelineStep):
        def execute(self, data):
            captured["formatter"] = data.get("formatter")
            return data

    mock_fmt = MagicMock()
    mock_fmt.emit_success.side_effect = typer.Exit(0)
    pipeline = Pipeline(
        steps=[_CaptureStep()],
        success_message="ok",
        formatter=mock_fmt,
    )
    with pytest.raises(typer.Exit):
        pipeline.run({})
    assert captured["formatter"] is mock_fmt


def test_pipeline_result_keys_only_includes_matching_keys():
    """Only keys listed in result_keys are passed to emit_success; extras are filtered."""
    mock_fmt = MagicMock()
    mock_fmt.emit_success.side_effect = typer.Exit(0)
    pipeline = Pipeline(
        steps=[_SuccessStep()],
        success_message="ok",
        result_keys=["label"],  # url excluded
        formatter=mock_fmt,
    )
    with pytest.raises(typer.Exit):
        pipeline.run({})
    mock_fmt.emit_success.assert_called_once_with("ok", data={"label": "my_fn"})
