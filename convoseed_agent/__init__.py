"""
convoseed-agent
===============
Capture, store, and retrieve agent conversation fingerprints.

Quick start:
    from convoseed_agent import ConvoSeedSession

    with ConvoSeedSession(task_type="summarization", success_score=0.9) as session:
        session.add_message("user", "Summarize this document...")
        session.add_message("assistant", "The document covers three main points...")
    # → ~/.convoseed/sessions/summarization_20260225_143022.fp
"""

from .encoder import (
    encode_conversation,
    read_fp_meta,
    read_fp_hdc,
    compare_fp,
    merge_fp,
    PROTOCOL_VERSION,
)
from .wrapper import ConvoSeedSession, convoseed_task
from .registry import (
    index_directory,
    query,
    build_consensus,
    list_task_types,
    stats,
)
from .cache import SkillCache, SkillPrefix
from .scheduler import run_once, start_daemon

__version__ = "1.1.0"
__author__ = "Ashraful"
__protocol__ = "CSP-1 v1.1"
