"""Debounced file watcher for sub-second incremental re-index."""

import os
import sys
import time
from typing import Callable, Optional, Set

from vinemap.graph.model import CodeGraph
from vinemap.graph.store import load_graph, load_raw_files, save_graph
from vinemap.license import effective_max_files
from vinemap.scanner.walker import iter_source_files, scan_project


def _poll_watch(
    root: str,
    interval: float = 1.0,
    debounce: float = 0.5,
    on_reindex: Optional[Callable[[dict], None]] = None,
) -> None:
    """Polling fallback when watchdog is unavailable."""
    root = os.path.abspath(root)
    mtimes: dict = {}
    pending: Set[str] = set()
    last_fire = 0.0

    for rel in iter_source_files(root):
        full = os.path.join(root, rel)
        try:
            mtimes[rel] = os.path.getmtime(full)
        except OSError:
            pass

    print(f"watching {root} (poll every {interval}s) — Ctrl+C to stop", file=sys.stderr)
    while True:
        time.sleep(interval)
        changed = False
        for rel in iter_source_files(root):
            full = os.path.join(root, rel)
            try:
                m = os.path.getmtime(full)
            except OSError:
                continue
            if mtimes.get(rel) != m:
                mtimes[rel] = m
                pending.add(rel)
                changed = True
        if not changed:
            continue
        now = time.time()
        if now - last_fire < debounce:
            continue
        last_fire = now
        n = len(pending)
        pending.clear()
        t0 = time.time()
        previous = load_raw_files(root)
        files, n_parsed, n_cached = scan_project(
            root, previous=previous, max_files=effective_max_files(None)
        )
        graph = CodeGraph.build(files)
        save_graph(root, graph)
        stats = graph.stats()
        dt = time.time() - t0
        msg = f"re-indexed {n} change(s) — {stats['files']} files in {dt:.2f}s"
        print(msg, file=sys.stderr)
        if on_reindex:
            on_reindex(stats)


def watch_project(root: str, interval: float = 1.0) -> None:
    """Watch project and re-index on save (watchdog if installed, else poll)."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        _poll_watch(root, interval=interval)
        return

    root = os.path.abspath(root)
    debounce_timer: list = [0.0]

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            debounce_timer[0] = time.time()

    def _loop(observer):
        print(f"watching {root} (watchdog) — Ctrl+C to stop", file=sys.stderr)
        last = 0.0
        try:
            while True:
                time.sleep(0.3)
                if debounce_timer[0] <= last:
                    continue
                if time.time() - debounce_timer[0] < 0.5:
                    continue
                last = debounce_timer[0]
                previous = load_raw_files(root)
                files, _, _ = scan_project(
                    root, previous=previous, max_files=effective_max_files(None)
                )
                graph = CodeGraph.build(files)
                save_graph(root, graph)
                print(f"re-indexed — {graph.stats()['files']} files", file=sys.stderr)
        except KeyboardInterrupt:
            observer.stop()

    observer = Observer()
    observer.schedule(Handler(), root, recursive=True)
    observer.start()
    _loop(observer)
    observer.join()
