"""
convoseed_agent.scheduler
=========================
Background merger — runs nightly, groups .fp files by task_type,
merges the top performers, writes a best-practice consensus fingerprint.

Can be run:
  - As a blocking loop:   python -m convoseed_agent.scheduler
  - As a one-shot:        python -m convoseed_agent.scheduler --once
  - Programmatically:     from convoseed_agent.scheduler import run_once, start_daemon
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path

from .registry import (
    index_directory,
    build_consensus,
    list_task_types,
    stats,
    DEFAULT_REGISTRY_DIR,
)

logger = logging.getLogger("convoseed.scheduler")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

DEFAULT_SESSIONS_DIR = DEFAULT_REGISTRY_DIR / "sessions"
MERGE_INTERVAL_SECONDS = 86_400   # 24 hours
MIN_SUCCESS_SCORE      = 0.5      # only merge sessions that worked
TOP_N_TO_MERGE         = 20       # merge best 20 per task type


def run_once(
    sessions_dir: Path = None,
    registry_dir: Path = None,
    min_score: float = MIN_SUCCESS_SCORE,
    top_n: int = TOP_N_TO_MERGE,
    verbose: bool = True,
) -> dict:
    """
    One full merge cycle:
      1. Re-index the sessions directory (picks up new .fp files)
      2. For every task_type in the registry, build a consensus fingerprint
      3. Return a summary dict

    Returns:
        {"indexed": int, "merged": int, "task_types": list[str], "timestamp": str}
    """
    sessions_dir = Path(sessions_dir or DEFAULT_SESSIONS_DIR).expanduser()
    registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()

    sessions_dir.mkdir(parents=True, exist_ok=True)
    registry_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if verbose:
        print(f"\n{'━'*55}")
        print(f"  🌙 ConvoSeed Nightly Merge  —  {ts}")
        print(f"{'━'*55}")

    # Step 1: index fresh sessions
    newly_indexed = index_directory(sessions_dir, registry_dir=registry_dir, verbose=verbose)

    # Step 2: get all task types
    task_rows = list_task_types(registry_dir)
    merged_count = 0
    merged_types = []

    for row in task_rows:
        task_type = row["task_type"]
        total     = row["total"]

        if total < 2:
            if verbose:
                print(f"  ⏭  '{task_type}' — only {total} session(s), skipping")
            continue

        if verbose:
            print(f"\n  📦 Merging '{task_type}'  ({total} sessions, avg score {row['avg_score']:.2f})")

        result = build_consensus(
            task_type,
            registry_dir=registry_dir,
            min_success_score=min_score,
            top_n=top_n,
            verbose=verbose,
        )

        if result is not None:
            merged_count += 1
            merged_types.append(task_type)

    # Step 3: summary
    s = stats(registry_dir)
    if verbose:
        print(f"\n{'━'*55}")
        print(f"  ✅ Merge complete")
        print(f"     Newly indexed : {newly_indexed}")
        print(f"     Types merged  : {merged_count} → {merged_types}")
        print(f"     Registry total: {s['total_fingerprints']} fingerprints across {s['task_types']} task types")
        print(f"{'━'*55}\n")

    return {
        "indexed": newly_indexed,
        "merged": merged_count,
        "task_types": merged_types,
        "timestamp": ts,
        "registry_stats": s,
    }


def start_daemon(
    sessions_dir: Path = None,
    registry_dir: Path = None,
    interval_seconds: int = MERGE_INTERVAL_SECONDS,
    run_immediately: bool = True,
) -> threading.Thread:
    """
    Start the merger as a background daemon thread.
    Returns the thread object (already started).

    Usage:
        daemon = start_daemon(run_immediately=True)
        # ... your main program runs ...
        # daemon runs nightly in background, no action needed
    """
    def _loop():
        if run_immediately:
            run_once(sessions_dir=sessions_dir, registry_dir=registry_dir)

        while True:
            next_run = datetime.now() + timedelta(seconds=interval_seconds)
            logger.info(f"Next merge scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(interval_seconds)
            run_once(sessions_dir=sessions_dir, registry_dir=registry_dir)

    t = threading.Thread(target=_loop, daemon=True, name="ConvoSeed-Merger")
    t.start()
    logger.info("Background merger daemon started")
    return t


# ── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ConvoSeed background merger")
    parser.add_argument("--once",     action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=MERGE_INTERVAL_SECONDS,
                        help="Seconds between merge runs (default: 86400 = 24h)")
    parser.add_argument("--sessions", default=None, help="Sessions directory")
    parser.add_argument("--registry", default=None, help="Registry directory")
    args = parser.parse_args()

    if args.once:
        run_once(sessions_dir=args.sessions, registry_dir=args.registry)
    else:
        print("ConvoSeed merger daemon running. Ctrl+C to stop.")
        try:
            start_daemon(
                sessions_dir=args.sessions,
                registry_dir=args.registry,
                interval_seconds=args.interval,
                run_immediately=True,
            )
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nDaemon stopped.")
