from pathlib import Path

from cli.commons.pipelines import Pipeline
from cli.commons.utils import sanitize_function_name
from cli.pages import pipelines
from cli.pages.models import PageTypeEnum


def create_page(
    name: str,
    verbose: bool,
    profile: str,
    type: PageTypeEnum,
):

    label = sanitize_function_name(name)
    project_path = Path.cwd() / name if not Path(name).is_absolute() else Path(name)
    steps = [
        pipelines.ValidateNotRunningFromPageDirectoryStep(),
        pipelines.ValidateCurrentPageExistsStep(),
        pipelines.GetActiveConfigStep(),
        pipelines.ValidatePagesAvailabilityPerPlanStep(),
        pipelines.ValidateTemplateStep(),
        pipelines.CreateProjectFolderStep(),
        pipelines.ExtractTemplateStep(),
        pipelines.ValidateExtractedPageStep(),
        pipelines.SaveManifestStep(),
        pipelines.EnsureDockerImageStep(),
    ]
    pipeline = Pipeline(
        steps, success_message=f"Page '{name}' created in '{project_path}'."
    )
    pipeline.run(
        {
            "verbose": verbose,
            "page_name": name,
            "page_label": label,
            "project_path": project_path,
            "profile": profile,
            "page_type": type,
            "clean_directory_if_validation_fails": True,
            "root": create_page.__name__,
        }
    )


def start_page(
    verbose: bool,
):
    steps = [
        pipelines.ValidatePageDirectoryStep(),
        pipelines.ReadPageMetadataStep(),
        pipelines.ValidatePageStructureStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetPageNameStep(),
        pipelines.ValidatePageNotRunningStep(),
        pipelines.EnsureFlaskManagerStep(),
        pipelines.StartPageContainerStep(),
        pipelines.PrintPageUrlStep(),
    ]
    pipeline = Pipeline(steps, success_message="Page started successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": start_page.__name__,
        }
    )


def stop_page(
    verbose: bool,
):
    steps = [
        pipelines.ValidatePageDirectoryStep(),
        pipelines.ReadPageMetadataStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetPageNameStep(),
        pipelines.ValidatePageRunningStep(),
        pipelines.StopPageContainerStep(),
    ]
    pipeline = Pipeline(steps, success_message="Page stopped successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": stop_page.__name__,
        }
    )


def restart_page(
    verbose: bool,
):
    steps = [
        pipelines.ValidatePageDirectoryStep(),
        pipelines.ReadPageMetadataStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetPageNameStep(),
        pipelines.ValidatePageRunningStep(),
        pipelines.StopPageContainerStep(),
        pipelines.EnsureFlaskManagerStep(),
        pipelines.StartPageContainerStep(),
        pipelines.PrintPageUrlStep(),
    ]
    pipeline = Pipeline(steps, success_message="Page restarted successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": restart_page.__name__,
        }
    )


def status_page(
    verbose: bool,
):
    steps = [
        pipelines.ValidatePageDirectoryStep(),
        pipelines.ReadPageMetadataStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetPageNameStep(),
        pipelines.GetPageStatusTableStep(),
        pipelines.PrintColoredTableStep(key="status"),
    ]
    pipeline = Pipeline(steps, success_message="")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": status_page.__name__,
        }
    )


def list_pages(
    verbose: bool,
):
    steps = [
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.ListAllPagesStep(),
        pipelines.PrintPagesListStep(),
    ]
    pipeline = Pipeline(steps, success_message="")
    pipeline.run(
        {
            "verbose": verbose,
            "root": list_pages.__name__,
        }
    )
