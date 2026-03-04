"""
ConvoSeed — fp_create.py
Generate a CSP-1 v2.0 .fp fingerprint file from a conversation.

Usage:
    # Identity fingerprint (captures how you write)
    python tools/fp_create.py --input conversation.json --output identity.fp --type identity

    # Skill fingerprint (captures how to do a task)
    python tools/fp_create.py --input conversation.json --output skill.fp --type skill --task "sentiment classification"

Input JSON format:
    [
        {"role": "user", "content": "message text"},
        {"role": "assistant", "content": "response text"},
        ...
    ]

Requirements:
    pip install anthropic sentence-transformers scikit-learn numpy
"""

import os
import json
import zipfile
import argparse
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer

SBERT_MODEL = "all-MiniLM-L6-v2"
HDC_DIM     = 10_000


# ── HDC encoding ──────────────────────────────────────────────────────────────
def hdc_encode(projected: np.ndarray, dim: int = HDC_DIM, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    R = rng.randn(projected.shape[1], dim).astype(np.float32)
    N = len(projected)
    superposition = np.zeros(dim, dtype=np.float32)
    for i, vec in enumerate(projected):
        h = np.sign(vec @ R).astype(np.float32)
        h[h == 0] = 1.0
        superposition += np.roll(h, N - 1 - i)
    result = np.sign(superposition)
    result[result == 0] = 1.0
    return result.astype(np.float16)


# ── LLM summary generation ────────────────────────────────────────────────────
def generate_summary(messages: list[dict], fp_type: str, task: str = "") -> str:
    try:
        import anthropic
        client = anthropic.Anthropic()

        if fp_type == "identity":
            examples = "\n".join(
                f'{i+1}. "{m["content"][:120]}"'
                for i, m in enumerate(messages[:6])
                if m.get("role") == "user"
            )
            prompt = f"""Analyze these messages written by one person and write a precise 80-100 word style description capturing:
- Sentence length and structure patterns
- Vocabulary level and register (formal/casual/technical)
- Use of hedging, certainty, or directness
- Characteristic phrases or punctuation habits
- Emotional tone and personality markers

Messages:
{examples}

Write ONLY the style description. No preamble."""

        else:  # skill
            exchanges = "\n".join(
                f'{"User" if m.get("role")=="user" else "Assistant"}: {m["content"][:150]}'
                for m in messages[:10]
            )
            prompt = f"""Given these examples of the task "{task}", write a precise 80-100 word skill description capturing:
- Step-by-step approach
- Key decision rules
- Common mistakes to avoid
- Edge cases to handle

Examples:
{exchanges}

Write ONLY the skill description. It will be injected as a system prompt prefix."""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    except ImportError:
        return f"[{fp_type.upper()} FINGERPRINT] Generated from {len(messages)} messages. Install anthropic package for LLM-generated summaries: pip install anthropic"
    except Exception as e:
        return f"[{fp_type.upper()} FINGERPRINT] Summary generation failed: {e}. Manual summary required."


# ── Main pipeline ─────────────────────────────────────────────────────────────
def create_fp(
    messages: list[dict],
    output_path: str,
    fp_type: str = "identity",
    task: str = "general",
    success_score: float = 0.0,
    model_name: str = "claude-sonnet-4-6"
) -> dict:
    """
    Generate a CSP-1 v2.0 .fp fingerprint file.

    Args:
        messages:      List of {role, content} dicts
        output_path:   Output .fp file path
        fp_type:       "identity" or "skill" or "combined"
        task:          Task description (for skill fingerprints)
        success_score: Quality rating 0.0-1.0
        model_name:    Model used to generate this fingerprint

    Returns:
        dict with statistics
    """
    texts = [m["content"] for m in messages if isinstance(m, dict) and m.get("content")]
    if not texts:
        raise ValueError("No message content found.")

    print(f"[1/4] Generating summary ({fp_type} fingerprint)...")
    summary = generate_summary(messages, fp_type, task)
    print(f"      Summary: {summary[:80]}...")

    print(f"[2/4] Embedding {len(texts)} messages with SBERT...")
    sbert = SentenceTransformer(SBERT_MODEL)
    vecs = sbert.encode(texts, show_progress_bar=False)

    print(f"[3/4] PCA + HDC encoding...")
    pca = PCA(n_components=min(len(texts), vecs.shape[1]))
    pca.fit(vecs)
    projected = pca.transform(vecs)
    hdc_vec = hdc_encode(projected)

    print(f"[4/4] Packing .fp file → {output_path}...")

    manifest = {
        "csp_version": "2.0",
        "fp_type": fp_type,
        "task_type": task,
        "success_score": success_score,
        "created": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "encoding": "text_summary+hdc_binary",
        "n_messages": len(texts)
    }

    metadata = {
        "sbert_model": SBERT_MODEL,
        "hdc_dim": HDC_DIM,
        "pca_components": pca.n_components_,
        "variance_k4": float(sum(pca.explained_variance_ratio_[:4])),
        "summary_words": len(summary.split()),
        "created": manifest["created"]
    }

    # Write ZIP
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("summary.txt", summary)
        zf.writestr("metadata.json", json.dumps(metadata, indent=2))
        if fp_type in ("identity", "combined"):
            zf.writestr("style_vector.bin", hdc_vec.tobytes())
        else:
            zf.writestr("task_vector.bin", hdc_vec.tobytes())

    size_kb = Path(output_path).stat().st_size / 1024
    sha256 = hashlib.sha256(Path(output_path).read_bytes()).hexdigest()[:12]

    print(f"\n✓  Fingerprint saved: {output_path}")
    print(f"   Size:     {size_kb:.1f} KB")
    print(f"   Type:     {fp_type}")
    print(f"   Task:     {task}")
    print(f"   Messages: {len(texts)}")
    print(f"   SHA256:   {sha256}...")
    print(f"\n   Inject with:")
    print(f"   import zipfile")
    print(f"   with zipfile.ZipFile('{output_path}') as fp:")
    print(f"       summary = fp.read('summary.txt').decode()")
    print(f"   system_prompt = summary + '\\n\\n' + your_prompt")

    return {"size_kb": size_kb, "n_messages": len(texts), "sha256": sha256}


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ConvoSeed fp_create — generate a CSP-1 v2.0 .fp fingerprint"
    )
    parser.add_argument("--input",          required=True,  help="Path to conversation JSON")
    parser.add_argument("--output",         required=True,  help="Output .fp file path")
    parser.add_argument("--type",           default="identity",
                        choices=["identity", "skill", "combined"],
                        help="Fingerprint type (default: identity)")
    parser.add_argument("--task",           default="general",
                        help="Task description for skill fingerprints")
    parser.add_argument("--success-score",  type=float, default=0.0,
                        help="Quality score 0.0-1.0 (default: 0.0)")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    messages = data if isinstance(data, list) else data.get("messages", [])
    create_fp(messages, args.output, args.type, args.task, args.success_score)
