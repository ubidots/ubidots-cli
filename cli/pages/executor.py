from pathlib import Path

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.pipelines import Pipeline
from cli.commons.utils import sanitize_function_name
from cli.pages import pipelines
from cli.pages.constants import PAGE_API_ROUTES
from cli.pages.models import PageTypeEnum


def create_local_page(
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
            "root": create_local_page.__name__,
        }
    )


def start_local_dev_server(
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
            "root": start_local_dev_server.__name__,
        }
    )


def stop_local_dev_server(
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
            "root": stop_local_dev_server.__name__,
        }
    )


def restart_local_dev_server(
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
            "root": restart_local_dev_server.__name__,
        }
    )


def show_local_dev_server_status(
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
            "root": show_local_dev_server_status.__name__,
        }
    )


def list_local_pages(
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
            "root": list_local_pages.__name__,
        }
    )


def list_pages_from_cloud_platform(
    profile: str,
    fields: str,
    sort_by: str,
    page_size: int,
    page: int,
    format: OutputFormatFieldsEnum,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.ListPagesFromRemoteServerStep(),
    ]
    pipeline = Pipeline(
        steps, success_message="Pages retrieved from remote server successfully."
    )
    pipeline.run(
        {
            "profile": profile,
            "format": format,
            "fields": fields,
            "sort_by": sort_by,
            "page_size": page_size,
            "page": page,
            "root": list_pages_from_cloud_platform.__name__,
        }
    )


def get_page_from_cloud_platform(
    page_key: str,
    profile: str,
    verbose: bool,
    format: OutputFormatFieldsEnum,
    fields: str,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.GetPageFromRemoteServerStep(),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "profile": profile,
            "page_key": page_key,
            "format": format,
            "fields": fields,
            "verbose": verbose,
            "root": get_page_from_cloud_platform.__name__,
        }
    )


def add_page_to_cloud_platform(
    profile: str,
    name: str,
    label: str,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.CreatePageRemoteServerStep(),
        pipelines.BuildPageEndpointStep(PAGE_API_ROUTES["code"]),
        pipelines.LoadTemplateZipStep(),
        pipelines.UploadPageCodeStep(),
        pipelines.CheckPageResponseStep("response"),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "profile": profile,
            "name": name,
            "label": label,
            "root": add_page_to_cloud_platform.__name__,
        }
    )


def delete_page_from_cloud_platform(
    page_key: str,
    profile: str,
    confirm: bool,
    verbose: bool,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.ConfirmOverwriteStep(),
        pipelines.DeletePageStep(),
    ]
    pipeline = Pipeline(steps, success_message=f"Page {page_key} deleted successfully.")
    pipeline.run(
        {
            "overwrite": {
                "confirm": confirm,
                "message": "Are you sure you want to delete the page?",
            },
            "profile": profile,
            "page_key": page_key,
            "verbose": verbose,
            "root": delete_page_from_cloud_platform.__name__,
        }
    )


def push_page_to_cloud_platform(
    confirm: bool,
    profile: str,
    verbose: bool,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.ReadPageMetadataStep(),
        pipelines.ValidatePageStructureStep(),
        pipelines.ValidateRemotePageExistStep(),
        pipelines.CreatePageIfNeededStep(),
        pipelines.SavePageRemoteIdStep(),
        pipelines.ConfirmOverwritePushPageStep(),
        pipelines.BuildPageEndpointStep(PAGE_API_ROUTES["code"]),
        pipelines.CompressPageProjectStep(),
        pipelines.UploadPageCodeStep(),
        pipelines.CheckPageResponseStep("response"),
    ]
    pipeline = Pipeline(steps, success_message="Page uploaded successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "profile": profile,
            "confirm": confirm,
            "verbose": verbose,
            "root": push_page_to_cloud_platform.__name__,
        }
    )


def pull_page_from_cloud_platform(
    remote_id: str,
    profile: str,
    confirm: bool = False,
    verbose: bool = False,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.CheckRemotePageIdRequirementStep(),
        pipelines.GetRemotePageDetailStep(),
        pipelines.CheckPageDetailResponseStep(),
        pipelines.ParsePageDetailsResponseStep(),
        pipelines.GetRemotePageLocalMetadataStep(),
        pipelines.ValidatePageHasAlreadyBeenPulledStep(),
        pipelines.ConfirmOverwritePullPageStep(),
        pipelines.DownloadPageCodeStep(),
        pipelines.CheckPageResponseStep("page_zip_content"),
        pipelines.ExtractPageProjectStep(),
        pipelines.SavePullPageManifestStep(),
        pipelines.PrintPagePathStep(),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "confirm": confirm,
            "profile": profile,
            "remote_id": remote_id,
            "verbose": verbose,
            "root": pull_page_from_cloud_platform.__name__,
        }
    )


def update_page_from_cloud_platform(
    page_key: str,
    new_name: str,
    profile: str,
    verbose: bool,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.UpdatePageStep(),
    ]
    pipeline = Pipeline(steps, success_message=f"Page {page_key} updated successfully.")
    pipeline.run(
        {
            "profile": profile,
            "page_key": page_key,
            "new_name": new_name,
            "verbose": verbose,
            "root": update_page_from_cloud_platform.__name__,
        }
    )


def logs_local_dev_server(
    tail: str,
    follow: bool,
    verbose: bool,
):
    steps = [
        pipelines.ValidatePageDirectoryStep(),
        pipelines.ReadPageMetadataStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetPageNameStep(),
        pipelines.GetPageLogsStep(tail=tail, follow=follow),
        pipelines.PrintkeyStep(key="logs"),
    ]
    pipeline = Pipeline(steps, success_message="")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": logs_local_dev_server.__name__,
        }
    )
