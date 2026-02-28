"""
convoseed_agent.cache
=====================
The agent skill cache — the part that closes the loop.

When a new agent session starts for a given task type, this module:
  1. Queries the registry for the consensus fingerprint
  2. Loads the HDC vector
  3. Returns a conditioning prefix (as a system prompt string, or as a
     numpy vector for native LLM prefix tuning)

This is what makes a new agent session NOT start from zero.
It inherits the reasoning patterns of every successful previous session
for that task type — compressed into 63KB, loaded in milliseconds.

Usage:
    from convoseed_agent.cache import SkillCache

    cache = SkillCache()

    # At session start — get the best known approach for this task
    prefix = cache.get_prefix("pdf_extraction")

    # Use it in your system prompt
    system_prompt = prefix.as_system_prompt()

    # Or get the raw numpy vector for native conditioning
    vector = prefix.as_vector()

    # After session ends, the new session auto-contributes back
    # (via ConvoSeedSession context manager)
"""

import json
import textwrap
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .encoder import read_fp_meta, read_fp_hdc
from .registry import query, DEFAULT_REGISTRY_DIR


@dataclass
class SkillPrefix:
    """
    A conditioning prefix derived from a consensus fingerprint.
    Represents the distilled reasoning wisdom for a task type.
    """
    task_type: str
    fp_id: str
    success_score: float
    n_sessions_merged: int
    task_description: str
    tags: list
    vector: np.ndarray          # HDC vector — 10,000 floats
    is_consensus: bool

    def as_system_prompt(self, style: str = "concise") -> str:
        """
        Convert the fingerprint into a human-readable system prompt
        that conditions the agent using natural language.

        In a full production system, this would be replaced by injecting
        the raw HDC vector as a prefix embedding directly into the LLM.
        This string version works with any API right now.
        """
        tags_str = ", ".join(self.tags) if self.tags else "general"
        source = "consensus of best past sessions" if self.is_consensus else "top past session"

        if style == "concise":
            return (
                f"[SKILL CACHE ACTIVE — {self.task_type}]\n"
                f"This session inherits reasoning patterns from {source} "
                f"(score: {self.success_score:.0%}, "
                f"based on {self.n_sessions_merged} prior session(s)).\n"
                f"Domain: {tags_str}.\n"
                f"Context: {self.task_description}\n"
                f"Apply the approach that worked before: be methodical, "
                f"flag edge cases early, and validate output structure before finishing."
            )

        elif style == "detailed":
            return textwrap.dedent(f"""
                [CONVOSEED SKILL CACHE — {self.task_type.upper()}]

                You are starting a new session with inherited skill context.
                A previous agent successfully completed this type of task
                with a success score of {self.success_score:.0%}.

                Task domain  : {tags_str}
                Prior context: {self.task_description}
                Source       : {source} ({self.n_sessions_merged} session(s))

                Apply what worked before:
                - Begin with structural analysis before attempting extraction
                - Flag ambiguous cases rather than guessing
                - Validate output schema before declaring completion
                - If encountering edge cases similar to prior sessions,
                  use conservative fallback strategies

                This context is automatically derived from ConvoSeed fingerprint
                {self.fp_id[:16]}... — a 63KB compressed skill fingerprint.
            """).strip()

        return self.as_system_prompt(style="concise")

    def as_vector(self) -> np.ndarray:
        """Raw HDC vector for native prefix embedding injection."""
        return self.vector.copy()

    def similarity_to(self, other: "SkillPrefix") -> float:
        """Cosine similarity between two skill prefixes."""
        a, b = self.vector, other.vector
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

    def __repr__(self):
        return (f"SkillPrefix(task='{self.task_type}', "
                f"score={self.success_score:.2f}, "
                f"sessions={self.n_sessions_merged})")


class SkillCache:
    """
    The agent skill cache.

    At session start  → cache.get_prefix(task_type)  → SkillPrefix
    At session end    → ConvoSeedSession context manager auto-saves
    Nightly           → scheduler.run_once() merges new sessions
    Next morning      → cache has a better prefix for that task type

    The loop is complete.
    """

    def __init__(self, registry_dir=None):
        self.registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR).expanduser()
        self._cache: dict[str, SkillPrefix] = {}  # in-memory cache

    def get_prefix(
        self,
        task_type: str,
        min_score: float = 0.5,
        prefer_consensus: bool = True,
        fallback_to_any: bool = True,
        verbose: bool = True,
    ) -> Optional[SkillPrefix]:
        """
        Retrieve the best skill prefix for a task type.

        Returns None if no relevant fingerprint exists yet
        (first time this task type has ever been run).

        Parameters
        ----------
        task_type       : e.g. "pdf_extraction"
        min_score       : only load fingerprints with score >= this
        prefer_consensus: prefer merged consensus over individual sessions
        fallback_to_any : if nothing above min_score, return best available
        verbose         : print cache hit/miss info
        """
        # Check in-memory cache first
        if task_type in self._cache:
            if verbose:
                print(f"[SkillCache] ⚡ In-memory hit for '{task_type}'")
            return self._cache[task_type]

        # Query registry
        results = query(
            task_type,
            registry_dir=self.registry_dir,
            top_k=1,
            min_score=min_score,
            consensus_only=prefer_consensus,
            verbose=False,
        )

        if not results and fallback_to_any:
            results = query(
                task_type,
                registry_dir=self.registry_dir,
                top_k=1,
                min_score=0.0,
                verbose=False,
            )

        if not results:
            if verbose:
                print(f"[SkillCache] ❌ MISS — no fingerprint for '{task_type}' yet")
                print(f"             This agent session will start cold.")
                print(f"             Its .fp will seed the cache for future sessions.")
            return None

        # Load the .fp file
        best = results[0]
        try:
            fp_bytes = Path(best["file_path"]).read_bytes()
            hdc = read_fp_hdc(fp_bytes)
            meta = read_fp_meta(fp_bytes)

            prefix = SkillPrefix(
                task_type      = task_type,
                fp_id          = best["fp_id"],
                success_score  = best["success_score"],
                n_sessions_merged = len(meta.get("merged_from", [])) or 1,
                task_description = best["task_description"],
                tags           = best["task_tags"],
                vector         = hdc,
                is_consensus   = best["is_consensus"],
            )

            # Store in memory cache
            self._cache[task_type] = prefix

            if verbose:
                source = "⭐ consensus" if best["is_consensus"] else "📄 single session"
                print(f"[SkillCache] ✅ HIT — '{task_type}'")
                print(f"             Source  : {source}")
                print(f"             Score   : {best['success_score']:.0%}")
                print(f"             Sessions: {prefix.n_sessions_merged}")
                print(f"             Tags    : {', '.join(best['task_tags']) or '—'}")

            return prefix

        except Exception as e:
            if verbose:
                print(f"[SkillCache] ⚠  Failed to load fingerprint: {e}")
            return None

    def warm(self, task_types: list[str], verbose: bool = True) -> dict:
        """
        Pre-load prefixes for multiple task types into memory.
        Call this at agent startup to avoid latency on first task.

        Returns dict of {task_type: SkillPrefix or None}
        """
        if verbose:
            print(f"[SkillCache] Warming cache for {len(task_types)} task types...")
        results = {}
        for tt in task_types:
            results[tt] = self.get_prefix(tt, verbose=False)

        hits = sum(1 for v in results.values() if v is not None)
        if verbose:
            print(f"[SkillCache] Cache warm: {hits}/{len(task_types)} hits\n")
        return results

    def invalidate(self, task_type: str = None):
        """Clear in-memory cache (force reload from disk on next get_prefix)."""
        if task_type:
            self._cache.pop(task_type, None)
        else:
            self._cache.clear()

    def list_available(self) -> list[str]:
        """Return all task types that have at least one fingerprint."""
        from .registry import list_task_types
        return [r["task_type"] for r in list_task_types(self.registry_dir)]
