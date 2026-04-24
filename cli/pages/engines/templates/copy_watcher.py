#!/usr/bin/env python3
"""Copy-watcher subprocess for pages dev server.

Watches source_dir for changes to manifest-tracked files and copies them
to workspace_dir. Re-renders index.html on body.html or manifest.toml changes.

Usage:
    python copy_watcher.py --source-dir /path/to/source --workspace-dir /path/to/workspace
"""
import argparse
import logging
import shutil
import threading
import time
from pathlib import Path

_DEBOUNCE_SECS = 0.2
_POLL_INTERVAL = 0.3


def _setup_logging(workspace_dir: Path) -> None:
    log_file = workspace_dir / ".copy_watcher.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def _get_tracked(source_dir: Path) -> list[Path]:
    from cli.pages.engines.helpers import get_tracked_files

    return get_tracked_files(source_dir)


def _copy_file(src: Path, source_dir: Path, workspace_dir: Path) -> None:
    try:
        rel = src.relative_to(source_dir)
        dst = workspace_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        logging.info("Copied %s", rel)
    except Exception as exc:
        logging.error("Failed to copy %s: %s", src, exc)


def _render(source_dir: Path, workspace_dir: Path) -> None:
    try:
        from cli.pages.engines.helpers import render_index_html

        hr_port_file = source_dir / ".hot_reload_port"
        if not hr_port_file.exists():
            logging.warning("No .hot_reload_port file; skipping index.html render")
            return
        hot_reload_port = int(hr_port_file.read_text().strip())
        render_index_html(source_dir, workspace_dir, hot_reload_port)
        logging.info("Rendered index.html")
    except Exception as exc:
        logging.error("Failed to render index.html: %s", exc)


def _copy_all(
    source_dir: Path,
    workspace_dir: Path,
    previous_tracked: set[str] | None = None,
) -> list[Path]:
    tracked = _get_tracked(source_dir)
    for f in tracked:
        _copy_file(f, source_dir, workspace_dir)

    if previous_tracked is not None:
        current = {str(f) for f in tracked}
        for old_str in previous_tracked - current:
            old_path = Path(old_str)
            try:
                rel = old_path.relative_to(source_dir)
            except ValueError:
                continue
            dst = workspace_dir / rel
            if dst.exists():
                dst.unlink()
                logging.info("Removed stale file %s", rel)

    return tracked


def _run_watchdog(
    source_dir: Path, workspace_dir: Path, skip_initial_copy: bool = False
) -> None:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    pending: dict[str, float] = {}
    lock = threading.Lock()

    tracked = (
        _get_tracked(source_dir)
        if skip_initial_copy
        else _copy_all(source_dir, workspace_dir)
    )
    if not skip_initial_copy:
        _render(source_dir, workspace_dir)
    tracked_set = {str(f) for f in tracked}

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory:
                with lock:
                    pending[event.src_path] = time.monotonic()

        def on_created(self, event):
            self.on_modified(event)

        def on_moved(self, event):
            with lock:
                pending[event.dest_path] = time.monotonic()

    observer = Observer()
    observer.schedule(_Handler(), str(source_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(_DEBOUNCE_SECS)
            with lock:
                now = time.monotonic()
                ready = {p for p, t in pending.items() if now - t >= _DEBOUNCE_SECS}
                for p in ready:
                    del pending[p]

            for path_str in ready:
                path = Path(path_str)
                if path == source_dir / "manifest.toml":
                    logging.info("manifest.toml changed — re-syncing all files")
                    try:
                        new_tracked = _copy_all(
                            source_dir, workspace_dir, previous_tracked=tracked_set
                        )
                        tracked_set.clear()
                        tracked_set.update(str(f) for f in new_tracked)
                        _render(source_dir, workspace_dir)
                    except Exception as exc:
                        logging.error("manifest.toml re-sync failed: %s", exc)
                elif path_str in tracked_set:
                    if not path.is_file():
                        tracked_set.discard(path_str)
                        try:
                            rel = path.relative_to(source_dir)
                            dst = workspace_dir / rel
                            if dst.exists():
                                dst.unlink()
                                logging.info("Removed deleted file %s", rel)
                        except Exception as exc:
                            logging.error("Failed to remove %s: %s", path, exc)
                    else:
                        _copy_file(path, source_dir, workspace_dir)
                        if path.name == "body.html":
                            _render(source_dir, workspace_dir)
                elif path.is_file():
                    try:
                        new_tracked = _get_tracked(source_dir)
                        new_set = {str(f) for f in new_tracked}
                        if path_str in new_set:
                            tracked_set.update(new_set)
                            _copy_file(path, source_dir, workspace_dir)
                    except Exception as exc:
                        logging.error("Failed to handle new file %s: %s", path, exc)
    finally:
        observer.stop()
        observer.join()


def _run_polling(
    source_dir: Path, workspace_dir: Path, skip_initial_copy: bool = False
) -> None:
    """Fallback: poll st_mtime at _POLL_INTERVAL seconds."""
    tracked = (
        _get_tracked(source_dir)
        if skip_initial_copy
        else _copy_all(source_dir, workspace_dir)
    )
    if not skip_initial_copy:
        _render(source_dir, workspace_dir)
    mtimes: dict[str, float] = {
        str(f): f.stat().st_mtime for f in tracked if f.exists()
    }

    while True:
        time.sleep(_POLL_INTERVAL)
        try:
            new_tracked = _get_tracked(source_dir)
        except Exception:
            new_tracked = tracked

        changed: list[Path] = []
        new_keys = {str(f) for f in new_tracked}
        for key in list(mtimes):
            if key not in new_keys or not Path(key).exists():
                del mtimes[key]
                try:
                    rel = Path(key).relative_to(source_dir)
                    dst = workspace_dir / rel
                    if dst.exists():
                        dst.unlink()
                        logging.info("Removed deleted file %s", rel)
                except Exception as exc:
                    logging.error("Failed to remove %s: %s", key, exc)
        for f in new_tracked:
            if not f.exists():
                continue
            key = str(f)
            mtime = f.stat().st_mtime
            if mtimes.get(key) != mtime:
                mtimes[key] = mtime
                changed.append(f)

        if any(f == source_dir / "manifest.toml" for f in changed):
            try:
                tracked = _copy_all(
                    source_dir, workspace_dir, previous_tracked=set(mtimes.keys())
                )
                mtimes = {str(f): f.stat().st_mtime for f in tracked if f.exists()}
                _render(source_dir, workspace_dir)
            except Exception as exc:
                logging.error("manifest.toml re-parse failed (poll): %s", exc)
        else:
            for f in changed:
                _copy_file(f, source_dir, workspace_dir)
                if f.name == "body.html":
                    _render(source_dir, workspace_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Page copy-watcher")
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--workspace-dir", required=True, type=Path)
    parser.add_argument(
        "--use-polling",
        action="store_true",
        help="Force st_mtime polling mode instead of watchdog",
    )
    parser.add_argument(
        "--skip-initial-copy",
        action="store_true",
        help="Skip initial file copy (files already copied by the caller)",
    )
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    workspace_dir = args.workspace_dir.resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)
    _setup_logging(workspace_dir)
    logging.info("Copy-watcher started: %s → %s", source_dir, workspace_dir)

    if args.use_polling:
        _run_polling(
            source_dir, workspace_dir, skip_initial_copy=args.skip_initial_copy
        )
    else:
        try:
            _run_watchdog(
                source_dir, workspace_dir, skip_initial_copy=args.skip_initial_copy
            )
        except ImportError:
            logging.warning("watchdog unavailable, falling back to polling")
            _run_polling(
                source_dir, workspace_dir, skip_initial_copy=args.skip_initial_copy
            )


if __name__ == "__main__":
    main()
