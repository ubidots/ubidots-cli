import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import httpx
import typer

from cli.commons.helpers import ARGO_CONTAINER_NAME
from cli.commons.helpers import ARGO_EXTERNAL_ADAPTER_PORT
from cli.commons.helpers import ARGO_EXTERNAL_TARGET_PORT
from cli.commons.helpers import ARGO_INTERNAL_ADAPTER_PORT
from cli.commons.helpers import ARGO_INTERNAL_TARGET_PORT
from cli.commons.helpers import argo_container_manager
from cli.commons.helpers import find_available_ports
from cli.commons.helpers import verify_and_fetch_images
from cli.commons.pipelines import PipelineStep
from cli.commons.settings import ARGO_IMAGE_NAME
from cli.commons.styles import print_colored_table
from cli.pages.engines.helpers import compute_workspace_key
from cli.pages.engines.helpers import deregister_page_from_argo
from cli.pages.engines.helpers import get_pages_workspace
from cli.pages.engines.helpers import get_tracked_files
from cli.pages.engines.helpers import register_page_in_argo
from cli.pages.engines.helpers import render_index_html
from cli.pages.engines.manager import PageEngineClientManager
from cli.pages.engines.settings import page_engine_settings
from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError
from cli.pages.helpers import read_page_manifest
from cli.pages.models import PageModelFactory
from cli.settings import settings


class ValidatePageDirectoryStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        manifest_file = project_path / settings.PAGES.PROJECT_MANIFEST_FILE
        if not manifest_file.exists():
            msg = (
                "Not in a page directory. Run this command inside a page project "
                "or use 'dev add' to create one."
            )
            raise FileNotFoundError(msg)
        return data


class ReadPageMetadataStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]

        try:
            data["project_metadata"] = read_page_manifest(project_path)
        except FileNotFoundError as err:
            msg = (
                "Not in a page directory. Run this command inside a page project "
                "or use 'dev add' to create one."
            )
            raise FileNotFoundError(msg) from err
        except Exception as e:
            msg = f"Failed to read page metadata: {e!s}"
            raise ValueError(msg) from e

        return data


class ValidatePageStructureStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        project_metadata = data["project_metadata"]
        page_type = project_metadata.project.type

        try:
            page_model = PageModelFactory.create_page_model_from_project(
                project_path, page_type
            )

            validation_result = page_model.validate_complete(project_path)

            if not validation_result["valid"]:
                errors = "; ".join(validation_result["errors"])
                msg = f"Page validation failed: {errors}"
                raise ValueError(msg)

            data["page_validation"] = validation_result
            data["page_model"] = page_model

        except Exception as e:
            msg = f"Page structure validation failed: {e!s}"
            raise ValueError(msg) from e

        return data


class GetClientStep(PipelineStep):
    def execute(self, data):
        engine_type = page_engine_settings.CONTAINER.DEFAULT_ENGINE
        manager = PageEngineClientManager(engine_type)
        client = manager.get_client()

        data["client"] = client
        return data


class GetContainerManagerStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        container_manager = client.get_container_manager()

        data["container_manager"] = container_manager
        return data


class GetPageNameStep(PipelineStep):
    def execute(self, data):
        project_metadata = data["project_metadata"]
        page_name = project_metadata.project.name

        data["page_name"] = page_name
        return data


class GetNetworkStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        network_manager = client.get_network_manager()
        networks = network_manager.list()
        network = next(iter(networks), None)
        if not network:
            network = network_manager.create()
        data["network"] = network
        return data


class GetArgoImageNameStep(PipelineStep):
    def execute(self, data):
        data["argo_image_name"] = ARGO_IMAGE_NAME
        return data


class ValidateArgoImageStep(PipelineStep):
    def execute(self, data):
        verify_and_fetch_images(
            client=data["client"], image_names=[data["argo_image_name"]]
        )
        return data


class EnsureArgoRunningStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        client = data["client"]
        network = data["network"]
        container, argo_adapter_port, argo_target_port = argo_container_manager(
            container_manager=container_manager,
            client=client,
            network=network,
            image_name=data["argo_image_name"],
        )
        data["argo_container"] = container
        data["argo_adapter_port"] = argo_adapter_port
        data["argo_target_port"] = argo_target_port
        return data


class TryGetArgoPortStep(PipelineStep):
    """Read Argo ports from the running container. Never starts Docker/Argo."""

    def execute(self, data):
        try:
            client = data["client"]
            container = client.client.containers.get(ARGO_CONTAINER_NAME)
            if container.status == "running":
                mapping_a = (container.ports or {}).get(ARGO_INTERNAL_ADAPTER_PORT, [])
                mapping_t = (container.ports or {}).get(ARGO_INTERNAL_TARGET_PORT, [])
                data["argo_adapter_port"] = (
                    int(mapping_a[0]["HostPort"])
                    if mapping_a
                    else ARGO_EXTERNAL_ADAPTER_PORT
                )
                data["argo_target_port"] = (
                    int(mapping_t[0]["HostPort"])
                    if mapping_t
                    else ARGO_EXTERNAL_TARGET_PORT
                )
            else:
                data["argo_adapter_port"] = None
                data["argo_target_port"] = None
        except Exception:
            data["argo_adapter_port"] = None
            data["argo_target_port"] = None
        return data


class FindHotReloadPortStep(PipelineStep):
    def execute(self, data):
        default = settings.PAGES.HOT_RELOAD_PORT_DEFAULT
        fallback_start = settings.PAGES.HOT_RELOAD_PORT_FALLBACK_START
        ports = find_available_ports([default], start_range=fallback_start)
        data["hot_reload_port"] = ports[0]
        return data


class RenderIndexHtmlStep(PipelineStep):
    def execute(self, data):
        render_index_html(
            data["project_path"],  # source_dir
            data["workspace_path"],  # workspace_dir
            data["hot_reload_port"],
        )
        return data


class RegisterPageInArgoStep(PipelineStep):
    def execute(self, data):
        register_page_in_argo(data["workspace_key"], data["argo_adapter_port"])
        return data


class StartHotReloadSubprocessStep(PipelineStep):
    def execute(self, data):
        hot_reload_script = (
            Path(__file__).parent.parent
            / "engines"
            / "templates"
            / "hot_reload_server.py"
        )
        log_file = data["workspace_path"] / ".hot_reload.log"
        with open(log_file, "w") as log:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(hot_reload_script),
                    "--page-workspace",
                    str(data["workspace_path"]),
                    "--port",
                    str(data["hot_reload_port"]),
                ],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        pid_file = data["project_path"] / ".pid"
        pid_file.write_text(str(proc.pid))
        data["hot_reload_process"] = proc
        return data


class DeregisterPageFromArgoStep(PipelineStep):
    def execute(self, data):
        deregister_page_from_argo(data["workspace_key"], data["argo_adapter_port"])
        return data


class StopHotReloadSubprocessStep(PipelineStep):
    def execute(self, data):
        pid_file = data["project_path"] / ".pid"
        if not pid_file.exists():
            return data
        pid = int(pid_file.read_text().strip())
        with suppress(ProcessLookupError, OSError):
            os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        stopped = False
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except (ProcessLookupError, OSError):
                stopped = True
                break
        if not stopped:
            with suppress(ProcessLookupError, OSError):
                os.kill(pid, signal.SIGKILL)
        pid_file.unlink(missing_ok=True)
        return data


class ShowPageLogsStep(PipelineStep):
    def execute(self, data):
        workspace = data["workspace_path"]
        copy_log = workspace / ".copy_watcher.log"
        hr_log = workspace / ".hot_reload.log"

        log_files = [str(f) for f in (copy_log, hr_log) if f.exists()]
        if not log_files:
            typer.echo("No log file found. Has the page been started?")
            return data

        tail = data.get("tail", "all")
        follow = data.get("follow", False)
        cmd = ["tail"]
        cmd += ["-n", tail if tail != "all" else "+1"]
        if follow:
            cmd.append("-f")
        cmd.extend(log_files)
        subprocess.run(cmd)
        return data


class StoreHotReloadPortStep(PipelineStep):
    def execute(self, data):
        (data["project_path"] / ".hot_reload_port").write_text(
            str(data["hot_reload_port"])
        )
        return data


class GetWorkspaceKeyStep(PipelineStep):
    def execute(self, data):
        page_name = data["page_name"]  # set by GetPageNameStep before this
        source_dir = data["project_path"]  # already the real source dir
        workspace_key = compute_workspace_key(page_name, source_dir)
        workspace_path = get_pages_workspace() / workspace_key
        data["workspace_key"] = workspace_key
        data["workspace_path"] = workspace_path
        # project_path is NOT changed — it stays as the source dir
        return data


class CreateWorkspaceStep(PipelineStep):
    def execute(self, data):
        data["workspace_path"].mkdir(parents=True, exist_ok=True)
        (data["workspace_path"] / ".source_path").write_text(
            str(data["project_path"]), encoding="utf-8"
        )
        return data


class CopyTrackedFilesStep(PipelineStep):
    def execute(self, data):
        source_dir = data["project_path"]
        workspace_dir = data["workspace_path"]
        tracked = get_tracked_files(source_dir)
        failures: list[str] = []
        for src_file in tracked:
            try:
                rel = src_file.relative_to(source_dir)
                dst = workspace_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst)
            except (OSError, ValueError) as exc:
                failures.append(f"{src_file}: {exc}")
        if failures:
            msg = "Failed to copy tracked page files:\n" + "\n".join(failures)
            raise RuntimeError(msg)
        return data


class StartCopyWatcherStep(PipelineStep):
    def execute(self, data):
        copy_watcher_script = (
            Path(__file__).parent.parent / "engines" / "templates" / "copy_watcher.py"
        )
        proc = subprocess.Popen(
            [
                sys.executable,
                str(copy_watcher_script),
                "--source-dir",
                str(data["project_path"]),
                "--workspace-dir",
                str(data["workspace_path"]),
                "--skip-initial-copy",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        (data["project_path"] / ".watcher.pid").write_text(str(proc.pid))
        return data


class StopCopyWatcherStep(PipelineStep):
    def execute(self, data):
        watcher_pid_file = data["project_path"] / ".watcher.pid"
        if not watcher_pid_file.exists():
            return data
        pid = int(watcher_pid_file.read_text().strip())
        with suppress(ProcessLookupError, OSError):
            os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        stopped = False
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except (ProcessLookupError, OSError):
                stopped = True
                break
        if not stopped:
            with suppress(ProcessLookupError, OSError):
                os.kill(pid, signal.SIGKILL)
        watcher_pid_file.unlink(missing_ok=True)
        return data


class ValidatePageNotRunningStep(PipelineStep):
    def execute(self, data):
        pid_file = data["project_path"] / ".pid"
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, 0)  # Signal 0 = check existence only
                workspace_key = data.get("workspace_key", data["project_path"].name)
                raise PageIsAlreadyRunningError(
                    name=workspace_key,
                    url=f"http://localhost:{ARGO_EXTERNAL_TARGET_PORT}/{workspace_key}/",
                )
            except ProcessLookupError:
                pid_file.unlink(missing_ok=True)  # Stale pid — clean up
            except PermissionError:
                workspace_key = data.get("workspace_key", data["project_path"].name)
                raise PageIsAlreadyRunningError(
                    name=workspace_key,
                    url=f"http://localhost:{ARGO_EXTERNAL_TARGET_PORT}/{workspace_key}/",
                ) from None
        return data


class ValidatePageRunningStep(PipelineStep):
    def execute(self, data):
        pid_file = data["project_path"] / ".pid"
        if not pid_file.exists():
            raise PageIsAlreadyStoppedError(name=data.get("workspace_key", ""))
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pid_file.unlink(missing_ok=True)
            raise PageIsAlreadyStoppedError(
                name=data.get("workspace_key", "")
            ) from None
        except PermissionError:
            pass  # Process exists (different user) — page is running
        return data


class GetPageStatusStep(PipelineStep):
    def execute(self, data):
        workspace_key = data.get("workspace_key", "")
        project_path = data.get("project_path")
        argo_port = data.get("argo_adapter_port", 8040)

        hot_reload_running = False
        if project_path:
            pid_file = project_path / ".pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    hot_reload_running = True
                except (ProcessLookupError, OSError):
                    pass

        argo_running = False
        try:
            resp = httpx.get(f"http://localhost:{argo_port}/api/_/route/", timeout=2.0)
            if resp.status_code == 200:
                for adapter in resp.json():
                    if adapter.get("label", "") == f"pages-{workspace_key}":
                        argo_running = True
                        break
        except Exception:
            pass

        status = "running" if (argo_running and hot_reload_running) else "stopped"
        argo_target_port = data.get("argo_target_port", ARGO_EXTERNAL_TARGET_PORT)
        url = (
            f"http://localhost:{argo_target_port}/{workspace_key}/"
            if argo_running
            else ""
        )

        data["page_status"] = status
        data["page_url"] = url

        return data


class GetPageStatusTableStep(PipelineStep):
    def execute(self, data):
        workspace_key = data.get("workspace_key", "")
        project_path = data.get("project_path")
        argo_port = data.get("argo_adapter_port")

        # Check hot reload subprocess
        hot_reload_running = False
        if project_path:
            pid_file = project_path / ".pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    hot_reload_running = True
                except (ProcessLookupError, OSError):
                    pass

        # Check Argo route
        argo_running = False
        if argo_port is not None:
            try:
                resp = httpx.get(
                    f"http://localhost:{argo_port}/api/_/route/", timeout=2.0
                )
                if resp.status_code == 200:
                    for adapter in resp.json():
                        if adapter.get("label", "") == f"pages-{workspace_key}":
                            argo_running = True
                            break
            except Exception:
                pass

        # Get browser errors from hot reload server
        browser_errors = []
        if hot_reload_running and project_path:
            hr_port_file = project_path / ".hot_reload_port"
            if hr_port_file.exists():
                try:
                    hr_port = int(hr_port_file.read_text().strip())
                    status_resp = httpx.get(
                        f"http://localhost:{hr_port}/__dev/status", timeout=2.0
                    )
                    if status_resp.status_code == 200:
                        browser_errors = status_resp.json().get("errors", [])
                except Exception:
                    pass

        status = "running" if (argo_running and hot_reload_running) else "stopped"
        argo_target_port = data.get("argo_target_port", ARGO_EXTERNAL_TARGET_PORT)
        url = (
            f"http://localhost:{argo_target_port}/{workspace_key}/"
            if argo_running
            else "-"
        )

        data["page_status"] = {
            "workspace_key": workspace_key,
            "status": status,
            "argo_running": argo_running,
            "hot_reload_running": hot_reload_running,
            "url": url,
            "browser_errors": browser_errors,
        }
        return data


class ListAllPagesStep(PipelineStep):
    def execute(self, data):
        workspace = get_pages_workspace()
        argo_port = data.get("argo_adapter_port", 8040)

        # Get active Argo routes
        active_keys: set[str] = set()
        try:
            resp = httpx.get(f"http://localhost:{argo_port}/api/_/route/", timeout=2)
            if resp.status_code == 200:
                for adapter in resp.json():
                    label = adapter.get("label", "")
                    if label.startswith("pages-"):
                        active_keys.add(label[len("pages-") :])
        except Exception:
            pass

        pages_info = []
        for page_dir in sorted(workspace.iterdir()):
            if not page_dir.is_dir():
                continue
            key = page_dir.name
            running = key in active_keys
            source_path_file = page_dir / ".source_path"
            if source_path_file.exists():
                source_path = source_path_file.read_text(encoding="utf-8").strip()
                source_missing = bool(source_path) and not Path(source_path).exists()
            else:
                source_path = "-"
                source_missing = True
            argo_target_port = data.get("argo_target_port", ARGO_EXTERNAL_TARGET_PORT)
            pages_info.append(
                {
                    "name": key,
                    "path": source_path,
                    "status": (
                        "orphaned"
                        if source_missing
                        else ("running" if running else "stopped")
                    ),
                    "url": (
                        f"http://localhost:{argo_target_port}/{key}/"
                        if running and not source_missing
                        else "-"
                    ),
                }
            )

        data["pages_info"] = pages_info
        return data


class PrintPageStatusStep(PipelineStep):
    def execute(self, data):
        page_name = data["page_name"]
        page_status = data["page_status"]
        status = page_status["status"]
        url = page_status.get("url", "")

        print(f"📄 Page: {page_name}")
        print(f"🔄 Status: {status}")

        if status == "running" and url and url != "-":
            print(f"🌐 URL: {url}")

        return data


class PrintPagesListStep(PipelineStep):
    def execute(self, data):
        pages_info = data.get("pages_info", [])

        if not pages_info:
            print("No pages found.")
            return data

        print_colored_table(
            results=pages_info, column_order=["name", "path", "status", "url"]
        )

        return data


class CleanOrphanedPagesStep(PipelineStep):
    def execute(self, data):
        workspace = get_pages_workspace()
        argo_port = data.get("argo_adapter_port", 8040)
        confirm = data.get("confirm", False)

        orphaned = []
        for page_dir in sorted(workspace.iterdir()):
            if not page_dir.is_dir():
                continue
            source_path_file = page_dir / ".source_path"
            if not source_path_file.exists():
                orphaned.append((page_dir.name, "(no source path)", page_dir))
                continue
            source_path = source_path_file.read_text(encoding="utf-8").strip()
            if source_path and not Path(source_path).exists():
                orphaned.append((page_dir.name, source_path, page_dir))

        if not orphaned:
            if not confirm:
                typer.echo("No orphaned pages found.")
            return data

        typer.echo(f"Found {len(orphaned)} orphaned page(s):")
        for name, source_path, _ in orphaned:
            typer.echo(f"  {name}  (source: {source_path})")
        typer.echo("")

        if not confirm and not typer.confirm("Remove all orphaned pages?"):
            raise typer.Abort

        removed = 0
        for name, _, page_dir in orphaned:
            with suppress(Exception):
                deregister_page_from_argo(name, argo_port)
            with suppress(Exception):
                shutil.rmtree(page_dir)
            typer.echo(f"  Removed {name}")
            removed += 1

        typer.echo(f"\nCleaned {removed} orphaned page(s).")
        return data


@dataclass
class PrintColoredTableStep(PipelineStep):
    key: str = ""

    def execute(self, data):
        if self.key and self.key in data:
            results = data[self.key]
            print_colored_table(results=results, column_order=["name", "status", "url"])
        return data


class PrintPageUrlStep(PipelineStep):
    def execute(self, data):
        workspace_key = data.get("workspace_key", "")
        argo_target_port = data.get("argo_target_port", ARGO_EXTERNAL_TARGET_PORT)
        if workspace_key:
            typer.echo(
                f"\n🌐 Page URL: http://localhost:{argo_target_port}/{workspace_key}/\n"
            )
        return data


@dataclass
class PrintkeyStep(PipelineStep):
    key: str = ""

    def execute(self, data):
        if self.key and self.key in data:
            typer.echo(data[self.key])
        return data
