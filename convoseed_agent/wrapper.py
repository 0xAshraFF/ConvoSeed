"""
convoseed_agent.wrapper
=======================
Context managers that wrap OpenAI / Anthropic API calls,
capture every message, and on exit encode the conversation
to a .fp fingerprint file.

Usage (OpenAI):
    with ConvoSeedSession(task_type="pdf_extraction") as session:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Extract tables from this PDF..."}]
        )
        session.add_message("user", "Extract tables from this PDF...")
        session.add_message("assistant", response.choices[0].message.content)
    # .fp written automatically on exit

Usage (Anthropic):
    with ConvoSeedSession(task_type="code_generation", output_dir="~/.convoseed") as session:
        session.track_anthropic(client, "claude-3-5-sonnet-20241022", messages, system)
    # .fp written automatically

Usage (manual / any provider):
    with ConvoSeedSession(task_type="web_scraping", success_score=0.9) as session:
        session.add_message("user", "Scrape this URL...")
        session.add_message("assistant", result_text)
"""

import os
import time
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .encoder import encode_conversation


DEFAULT_OUTPUT_DIR = Path.home() / ".convoseed" / "sessions"


class ConvoSeedSession:
    """
    Context manager that records an agent conversation and encodes it
    to a .fp file on exit.

    Parameters
    ----------
    task_type : str
        Short identifier like "pdf_extraction", "web_scraping", "summarization".
        Used by the registry to group similar tasks.
    task_description : str
        Human-readable description of what the task was.
    task_tags : list[str]
        Free-form tags e.g. ["pdf", "finance", "tables"].
    success_score : float
        0.0 = complete failure, 1.0 = perfect success.
        Set this before the context exits, or pass to __exit__.
    output_dir : str or Path
        Where to save the .fp file. Default: ~/.convoseed/sessions/
    pca_k : int
        PCA compression components. 16 is the recommended default.
    auto_score : bool
        If True, prompts user for success score in terminal on exit.
    silent : bool
        Suppress all print output.
    """

    def __init__(
        self,
        task_type: str = "general",
        task_description: str = "",
        task_tags: list = None,
        success_score: float = 0.0,
        output_dir=None,
        pca_k: int = 16,
        auto_score: bool = False,
        silent: bool = False,
    ):
        self.task_type = task_type
        self.task_description = task_description
        self.task_tags = task_tags or []
        self.success_score = success_score
        self.output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR).expanduser()
        self.pca_k = pca_k
        self.auto_score = auto_score
        self.silent = silent
        self.messages: list[dict] = []
        self._start_time = None
        self._fp_path: Optional[Path] = None

    def __enter__(self):
        self._start_time = time.time()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.silent:
            print(f"[ConvoSeed] Session started — task: '{self.task_type}'")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # If an exception occurred, mark as failed unless already set
        if exc_type is not None and self.success_score == 0.0:
            self.success_score = 0.0

        if self.auto_score and not self.silent:
            try:
                raw = input("[ConvoSeed] Rate success 0.0–1.0 (Enter to skip): ").strip()
                if raw:
                    self.success_score = max(0.0, min(1.0, float(raw)))
            except (ValueError, EOFError):
                pass

        if len(self.messages) < 2:
            if not self.silent:
                print("[ConvoSeed] ⚠  Fewer than 2 messages — skipping encode.")
            return False

        try:
            fp_bytes = encode_conversation(
                self.messages,
                task_type=self.task_type,
                success_score=self.success_score,
                task_tags=self.task_tags,
                task_description=self.task_description,
                pca_k=self.pca_k,
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_task = self.task_type.replace(" ", "_").replace("/", "-")
            filename = f"{safe_task}_{timestamp}.fp"
            self._fp_path = self.output_dir / filename

            self._fp_path.write_bytes(fp_bytes)

            if not self.silent:
                duration = time.time() - self._start_time
                print(f"[ConvoSeed] ✓ Encoded {len(self.messages)} messages → {self._fp_path.name}")
                print(f"[ConvoSeed]   Size: {len(fp_bytes)/1024:.1f} KB  |  "
                      f"Task: {self.task_type}  |  "
                      f"Score: {self.success_score:.2f}  |  "
                      f"Duration: {duration:.1f}s")

        except Exception as e:
            if not self.silent:
                print(f"[ConvoSeed] ✗ Encode failed: {e}")

        return False  # Don't suppress exceptions

    # ── Message recording ────────────────────────────────────────────────────

    def add_message(self, role: str, text: str):
        """
        Manually add a message to the session.
        role: "user", "assistant", "ai", "system"
        """
        if text and text.strip():
            self.messages.append({"role": role, "text": text.strip()})

    def add_messages(self, messages: list[dict]):
        """Add multiple messages at once from a list of {role, content/text} dicts."""
        for m in messages:
            text = m.get("content") or m.get("text") or ""
            role = m.get("role", "user")
            self.add_message(role, text)

    def set_success(self, score: float):
        """Set success score (0.0–1.0). Call before context exits."""
        self.success_score = max(0.0, min(1.0, float(score)))

    # ── Provider-specific helpers ────────────────────────────────────────────

    def track_openai(self, client, model: str, messages: list[dict], **kwargs):
        """
        Drop-in wrapper around client.chat.completions.create().
        Records input messages and response automatically.

        Example:
            response = session.track_openai(client, "gpt-4o", messages)
        """
        # Record input messages
        self.add_messages(messages)

        # Make the actual API call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )

        # Record response
        for choice in response.choices:
            content = choice.message.content or ""
            self.add_message("assistant", content)

        return response

    def track_anthropic(self, client, model: str, messages: list[dict],
                        system: str = "", **kwargs):
        """
        Drop-in wrapper around client.messages.create().
        Records messages and response automatically.

        Example:
            response = session.track_anthropic(client, "claude-3-5-sonnet-20241022", messages)
        """
        if system:
            self.add_message("system", system)

        self.add_messages(messages)

        response = client.messages.create(
            model=model,
            messages=messages,
            system=system,
            **kwargs
        )

        # Record response content blocks
        for block in response.content:
            if hasattr(block, "text"):
                self.add_message("assistant", block.text)

        return response

    @property
    def fp_path(self) -> Optional[Path]:
        """Path to the written .fp file, available after context exit."""
        return self._fp_path


# ── Convenience decorator ────────────────────────────────────────────────────

def convoseed_task(
    task_type: str = "general",
    task_tags: list = None,
    output_dir=None,
    auto_score: bool = True,
):
    """
    Decorator that wraps an async or sync agent function with ConvoSeed recording.

    The decorated function receives a `session: ConvoSeedSession` kwarg it can
    use to add messages. On return, the session is encoded automatically.

    Example:
        @convoseed_task(task_type="summarization", task_tags=["text", "finance"])
        def run_agent(query: str, session: ConvoSeedSession = None):
            session.add_message("user", query)
            result = my_llm_call(query)
            session.add_message("assistant", result)
            session.set_success(0.95)
            return result
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ConvoSeedSession(
                task_type=task_type,
                task_tags=task_tags or [],
                output_dir=output_dir,
                auto_score=auto_score,
            ) as session:
                kwargs["session"] = session
                return func(*args, **kwargs)
        return wrapper

    return decorator
