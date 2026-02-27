"""
ConvoSeed — encode.py
Encodes a conversation into a CSP-1 .fp fingerprint file.

Usage:
    python encode.py --input conversation.json --output identity.fp

Input JSON format:
    [
        {"role": "user", "content": "message text"},
        {"role": "assistant", "content": "response text"},
        ...
    ]

Requirements:
    pip install sentence-transformers scikit-learn numpy cryptography
"""

import json
import argparse
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer

# ── Configuration ─────────────────────────────────────────────────────────────
SBERT_MODEL = "all-MiniLM-L6-v2"   # 384-dim, fast, good quality
HDC_DIM     = 10_000                # hypervector dimension
PREFIX_LEN  = 20                    # prefix tokens for generation
CHUNK_SIZE  = 50                    # messages per CHUNKS entry

# ── Helpers ───────────────────────────────────────────────────────────────────
def embed_messages(messages: list[str], model: SentenceTransformer) -> np.ndarray:
    """Encode messages to 384-dim SBERT vectors. Shape: (N, 384)"""
    return model.encode(messages, show_progress_bar=True, normalize_embeddings=False)


def fit_pca(vecs: np.ndarray) -> PCA:
    """Fit full PCA on message embeddings. Lossless — retains all components."""
    pca = PCA(n_components=None)
    pca.fit(vecs)
    return pca


def hdc_bind_sequence(projected: np.ndarray, dim: int = HDC_DIM,
                       seed: int = 42) -> np.ndarray:
    """
    Bind sequence of projected vectors into one HDC hypervector.

    Encoding:
        1. Project each row via random matrix R → sign → binary {-1, +1}^D
        2. Bind with cyclic-shift position encoding:
           result = shift(h1, N-1) XOR shift(h2, N-2) XOR ... XOR hN
        3. Threshold superposition to {-1, +1}
    """
    rng = np.random.RandomState(seed)
    k = projected.shape[1]
    R = rng.randn(k, dim).astype(np.float32)   # projection matrix

    N = len(projected)
    superposition = np.zeros(dim, dtype=np.float32)

    for i, vec in enumerate(projected):
        # Encode individual vector
        h = np.sign(vec @ R).astype(np.float32)
        h[h == 0] = 1.0   # break ties

        # Cyclic shift by position (N-1-i for causal binding)
        shift = N - 1 - i
        h_shifted = np.roll(h, shift)

        superposition += h_shifted

    # Threshold to {-1, +1}
    bound = np.sign(superposition)
    bound[bound == 0] = 1.0
    return bound.astype(np.float16)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    a, b = a.astype(np.float32), b.astype(np.float32)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# ── Main encode pipeline ──────────────────────────────────────────────────────
def encode_conversation(messages: list[str], output_path: str,
                         user_only: bool = True) -> dict:
    """
    Full CSP-1 encode pipeline.

    Args:
        messages:    List of message strings (or dicts with 'content' key)
        output_path: Where to save the .fp file
        user_only:   If True, only encode user messages (recommended)

    Returns:
        dict with statistics about the encoding
    """
    # Normalise input
    texts = []
    for m in messages:
        if isinstance(m, dict):
            if user_only and m.get("role") != "user":
                continue
            texts.append(m["content"])
        else:
            texts.append(str(m))

    if len(texts) == 0:
        raise ValueError("No messages to encode. Check your input format and user_only setting.")

    print(f"[1/4] Embedding {len(texts)} messages with SBERT ({SBERT_MODEL})...")
    model = SentenceTransformer(SBERT_MODEL)
    vecs = embed_messages(texts, model)
    print(f"      Embedding shape: {vecs.shape}")

    print(f"[2/4] Fitting PCA on embeddings...")
    pca = fit_pca(vecs)
    projected = pca.transform(vecs)
    print(f"      Style centroid: mean={pca.mean_.shape}, components={pca.components_.shape}")
    print(f"      Variance in k=4 components: {sum(pca.explained_variance_ratio_[:4]):.1%}")

    print(f"[3/4] HDC binding ({HDC_DIM}-dim hypervector)...")
    seed_vec = hdc_bind_sequence(projected, dim=HDC_DIM)
    print(f"      Seed shape: {seed_vec.shape}, dtype: {seed_vec.dtype}")

    print(f"[4/4] Saving .fp file to {output_path}...")
    fp_data = {
        "version": "0.2",
        "n_messages": len(texts),
        "embed_dim": vecs.shape[1],
        "n_components": pca.components_.shape[0],
        "pca_mean": pca.mean_.tolist(),
        "pca_components": pca.components_.tolist(),
        "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "hdc_dim": HDC_DIM,
        "hdc_seed": seed_vec.tolist(),
        # NOTE: In v0.2, PREFIX is trained separately — see decode.py
        # NOTE: SIGNATURE requires your private key — see sign.py (TODO)
    }

    with open(output_path, "w") as f:
        json.dump(fp_data, f)

    file_size_kb = Path(output_path).stat().st_size / 1024
    print(f"\n✓  Fingerprint saved: {output_path}")
    print(f"   File size:   {file_size_kb:.1f} KB")
    print(f"   Messages:    {len(texts)}")
    print(f"   Embed dim:   {vecs.shape[1]}")
    print(f"   HDC dim:     {HDC_DIM}")

    return {
        "n_messages": len(texts),
        "file_size_kb": file_size_kb,
        "variance_k4": float(sum(pca.explained_variance_ratio_[:4]))
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ConvoSeed Encoder — compress a conversation to a .fp fingerprint"
    )
    parser.add_argument("--input",  required=True, help="Path to conversation JSON file")
    parser.add_argument("--output", required=True, help="Output .fp file path")
    parser.add_argument("--all-messages", action="store_true",
                        help="Encode all messages (default: user messages only)")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    # Accept both list of strings and list of {role, content} dicts
    messages = data if isinstance(data, list) else data.get("messages", [])

    encode_conversation(messages, args.output, user_only=not args.all_messages)
