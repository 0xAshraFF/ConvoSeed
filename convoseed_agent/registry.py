"""
convoseed_agent.registry
========================
Local registry for .fp fingerprint files.

- Indexes a directory of .fp files into a SQLite database
- Groups by task_type, merges top performers nightly
- CLI: convoseed query --task "pdf_extraction" --top 3
"""

import os
import json
import sqlite3
import struct
import argparse
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np

from .encoder import read_fp_meta, read_fp_hdc, merge_fp, compare_fp

DEFAULT_REGISTRY_DIR = Path.home() / ".convoseed"
DB_NAME = "registry.db"


# ── Database ─────────────────────────────────────────────────────────────────

def _get_db(registry_dir: Path) -> sqlite3.Connection:
    registry_dir.mkdir(parents=True, exist_ok=True)
    db_path = registry_dir / DB_NAME
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            fp_id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'general',
            task_description TEXT DEFAULT '',
            task_tags TEXT DEFAULT '[]',
            success_score REAL DEFAULT 0.0,
            n_messages INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT 0,
            is_consensus INTEGER DEFAULT 0,
            file_size_kb REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    return conn


# ── Indexer ───────────────────────────────────────────────────────────────────

def index_directory(
    directory: str | Path,
    registry_dir: str | Path = None,
    verbose: bool = True,
) -> int:
    """
    Walk a directory, read every .fp file, add to registry.
    Returns number of newly indexed files.
    """
    directory = Path(directory).expanduser()
    registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()
    conn = _get_db(registry_dir)

    new_count = 0
    errors = 0

    fp_files = list(directory.rglob("*.fp"))
    if verbose:
        print(f"[Registry] Scanning {directory} — found {len(fp_files)} .fp files")

    for fp_path in fp_files:
        try:
            raw = fp_path.read_bytes()
            meta = read_fp_meta(raw)
            fp_id = meta.get("fp_id", str(fp_path))

            # Skip consensus files from re-indexing (they're generated internally)
            existing = conn.execute(
                "SELECT fp_id FROM fingerprints WHERE fp_id = ?", (fp_id,)
            ).fetchone()
            if existing:
                continue

            conn.execute("""
                INSERT OR REPLACE INTO fingerprints
                (fp_id, file_path, task_type, task_description, task_tags,
                 success_score, n_messages, created_at, is_consensus, file_size_kb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                fp_id,
                str(fp_path),
                meta.get("task_type", "general"),
                meta.get("task_description", ""),
                json.dumps(meta.get("task_tags", [])),
                float(meta.get("success_score", 0.0)),
                int(meta.get("n_messages", 0)),
                int(meta.get("created_at", 0)),
                len(raw) / 1024,
            ))
            new_count += 1

        except Exception as e:
            if verbose:
                print(f"[Registry] ⚠  Skip {fp_path.name}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    if verbose:
        print(f"[Registry] ✓ Indexed {new_count} new files  ({errors} errors)")
    return new_count


# ── Merger ────────────────────────────────────────────────────────────────────

def build_consensus(
    task_type: str,
    registry_dir: str | Path = None,
    min_success_score: float = 0.5,
    top_n: int = 20,
    verbose: bool = True,
) -> Optional[bytes]:
    """
    Merge the top-N highest-scoring .fp files for a task_type
    into one consensus fingerprint.
    """
    registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()
    conn = _get_db(registry_dir)

    rows = conn.execute("""
        SELECT fp_id, file_path, success_score, n_messages
        FROM fingerprints
        WHERE task_type = ?
          AND success_score >= ?
          AND is_consensus = 0
        ORDER BY success_score DESC, n_messages DESC
        LIMIT ?
    """, (task_type, min_success_score, top_n)).fetchall()

    conn.close()

    if len(rows) < 2:
        if verbose:
            print(f"[Registry] Not enough data to merge '{task_type}' "
                  f"(need ≥2, found {len(rows)})")
        return None

    fp_bytes_list = []
    weights = []

    for fp_id, file_path, score, n_msg in rows:
        try:
            raw = Path(file_path).read_bytes()
            fp_bytes_list.append(raw)
            weights.append(score)
        except Exception as e:
            if verbose:
                print(f"[Registry] ⚠  Cannot read {file_path}: {e}")

    if len(fp_bytes_list) < 2:
        return None

    if verbose:
        print(f"[Registry] Merging {len(fp_bytes_list)} fingerprints for '{task_type}'...")

    consensus = merge_fp(fp_bytes_list, weights=weights)

    # Save consensus .fp
    consensus_dir = registry_dir / "consensus"
    consensus_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = consensus_dir / f"consensus_{task_type}_{ts}.fp"
    out_path.write_bytes(consensus)

    # Register it
    meta = read_fp_meta(consensus)
    conn2 = _get_db(registry_dir)
    conn2.execute("""
        INSERT OR REPLACE INTO fingerprints
        (fp_id, file_path, task_type, task_description, task_tags,
         success_score, n_messages, created_at, is_consensus, file_size_kb)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        meta["fp_id"],
        str(out_path),
        task_type,
        meta.get("task_description", f"Consensus for {task_type}"),
        json.dumps(meta.get("task_tags", [])),
        float(meta.get("success_score", 0.0)),
        int(meta.get("n_messages", 0)),
        int(meta.get("created_at", 0)),
        len(consensus) / 1024,
    ))
    conn2.commit()
    conn2.close()

    if verbose:
        print(f"[Registry] ✓ Consensus saved → {out_path.name} ({len(consensus)/1024:.1f} KB)")

    return consensus


# ── Query ─────────────────────────────────────────────────────────────────────

def query(
    task_type: str,
    registry_dir: str | Path = None,
    top_k: int = 3,
    top: int = None,
    min_score: float = 0.0,
    consensus_only: bool = False,
    verbose: bool = True,
) -> list[dict]:
    """
    Return top-k fingerprints for a task type, ranked by success_score.
    `top` is an alias for `top_k`.
    """
    if top is not None:
        top_k = top
    registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()
    conn = _get_db(registry_dir)

    where_parts = ["task_type = ?", "success_score >= ?"]
    params = [task_type, min_score]

    if consensus_only:
        where_parts.append("is_consensus = 1")

    rows = conn.execute(f"""
        SELECT fp_id, file_path, task_type, task_description, task_tags,
               success_score, n_messages, created_at, is_consensus, file_size_kb
        FROM fingerprints
        WHERE {' AND '.join(where_parts)}
        ORDER BY is_consensus DESC, success_score DESC, n_messages DESC
        LIMIT ?
    """, [*params, top_k]).fetchall()

    conn.close()

    results = []
    for row in rows:
        results.append({
            "fp_id": row[0],
            "file_path": row[1],
            "task_type": row[2],
            "task_description": row[3],
            "task_tags": json.loads(row[4] or "[]"),
            "success_score": row[5],
            "n_messages": row[6],
            "created_at": row[7],
            "is_consensus": bool(row[8]),
            "file_size_kb": row[9],
        })

    if verbose:
        _print_results(task_type, results)

    return results


def list_task_types(registry_dir: str | Path = None) -> list[dict]:
    """List all task types in the registry with counts."""
    registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()
    conn = _get_db(registry_dir)
    rows = conn.execute("""
        SELECT task_type,
               COUNT(*) as total,
               SUM(is_consensus) as consensus_count,
               AVG(success_score) as avg_score,
               MAX(created_at) as latest
        FROM fingerprints
        GROUP BY task_type
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return [
        {"task_type": r[0], "total": r[1], "consensus": r[2],
         "avg_score": round(r[3], 3), "latest": r[4]}
        for r in rows
    ]


def stats(registry_dir: str | Path = None) -> dict:
    """Overall registry statistics."""
    registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()
    conn = _get_db(registry_dir)
    row = conn.execute("""
        SELECT COUNT(*), SUM(is_consensus), AVG(success_score),
               SUM(file_size_kb), COUNT(DISTINCT task_type)
        FROM fingerprints
    """).fetchone()
    conn.close()
    return {
        "total_fingerprints": row[0] or 0,
        "consensus_fingerprints": row[1] or 0,
        "avg_success_score": round(row[2] or 0, 3),
        "total_size_kb": round(row[3] or 0, 1),
        "task_types": row[4] or 0,
    }


# ── Pretty printer ────────────────────────────────────────────────────────────

def _print_results(task_type: str, results: list[dict]):
    if not results:
        print(f"\n[Registry] No results found for task_type='{task_type}'")
        print("  → Run: convoseed index <directory>  to add fingerprints")
        return

    print(f"\n{'═'*60}")
    print(f"  TOP {len(results)} FINGERPRINTS — task: '{task_type}'")
    print(f"{'═'*60}")

    for i, r in enumerate(results, 1):
        badge = "⭐ CONSENSUS" if r["is_consensus"] else f"#{i}"
        score_bar = "█" * int(r["success_score"] * 10) + "░" * (10 - int(r["success_score"] * 10))
        print(f"""
  {badge}
  ID:      {r['fp_id'][:16]}...
  Score:   [{score_bar}] {r['success_score']:.2f}
  File:    {Path(r['file_path']).name}
  Size:    {r['file_size_kb']:.1f} KB   Messages: {r['n_messages']}
  Tags:    {', '.join(r['task_tags']) or '—'}
  Desc:    {textwrap.shorten(r['task_description'] or '—', 55)}""")

    print(f"\n{'─'*60}")
    print("  Load the top result:")
    if results:
        print(f"  fp_bytes = open('{results[0]['file_path']}', 'rb').read()")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli_main():
    parser = argparse.ArgumentParser(
        prog="convoseed",
        description="ConvoSeed Registry — local .fp fingerprint manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          convoseed index ~/.convoseed/sessions
          convoseed query --task pdf_extraction --top 3
          convoseed merge --task pdf_extraction
          convoseed stats
          convoseed tasks
        """),
    )

    sub = parser.add_subparsers(dest="command")

    # index
    p_index = sub.add_parser("index", help="Index a directory of .fp files")
    p_index.add_argument("directory", help="Path to scan for .fp files")
    p_index.add_argument("--registry", default=None, help="Registry directory")

    # query
    p_query = sub.add_parser("query", help="Find top fingerprints for a task")
    p_query.add_argument("--task", required=True, help="Task type e.g. pdf_extraction")
    p_query.add_argument("--top", type=int, default=3, help="Number of results")
    p_query.add_argument("--min-score", type=float, default=0.0)
    p_query.add_argument("--consensus-only", action="store_true")
    p_query.add_argument("--registry", default=None)

    # merge / build consensus
    p_merge = sub.add_parser("merge", help="Build consensus fingerprint for a task")
    p_merge.add_argument("--task", required=True, help="Task type to merge")
    p_merge.add_argument("--min-score", type=float, default=0.5)
    p_merge.add_argument("--top-n", type=int, default=20)
    p_merge.add_argument("--registry", default=None)

    # stats
    p_stats = sub.add_parser("stats", help="Overall registry statistics")
    p_stats.add_argument("--registry", default=None, help="Registry directory")

    # tasks
    p_tasks = sub.add_parser("tasks", help="List all task types in registry")
    p_tasks.add_argument("--registry", default=None, help="Registry directory")

    args = parser.parse_args()

    if args.command == "index":
        index_directory(args.directory, registry_dir=args.registry)

    elif args.command == "query":
        query(
            args.task,
            registry_dir=args.registry,
            top_k=args.top,
            min_score=args.min_score,
            consensus_only=args.consensus_only,
        )

    elif args.command == "merge":
        build_consensus(
            args.task,
            registry_dir=args.registry,
            min_success_score=args.min_score,
            top_n=args.top_n,
        )

    elif args.command == "stats":
        s = stats(args.registry)
        print(f"""
[ConvoSeed Registry]
  Total fingerprints : {s['total_fingerprints']}
  Consensus files    : {s['consensus_fingerprints']}
  Task types         : {s['task_types']}
  Avg success score  : {s['avg_success_score']}
  Total size         : {s['total_size_kb']:.1f} KB
""")

    elif args.command == "tasks":
        tasks = list_task_types(args.registry)
        if not tasks:
            print("[Registry] Empty — run: convoseed index <dir>")
            return
        print(f"\n{'─'*55}")
        print(f"  {'TASK TYPE':<25} {'COUNT':>5}  {'AVG SCORE':>9}  {'CONSENSUS':>9}")
        print(f"{'─'*55}")
        for t in tasks:
            print(f"  {t['task_type']:<25} {t['total']:>5}  {t['avg_score']:>9.3f}  {t['consensus']:>9}")
        print(f"{'─'*55}\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
