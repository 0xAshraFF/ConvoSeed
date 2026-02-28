"""
ConvoSeed CSP-1 v1.1 Encoder
Adds: task_type, success_score, task_tags, task_description to metadata.

v1.0 → v1.1 changelog:
  - META_JSON now includes task_type (str), success_score (float 0-1),
    task_tags (list[str]), task_description (str)
  - These fields are OPTIONAL in v1.1 (backward compatible, MINOR bump)
  - Protocol version field bumped to "1.1.0"
"""

import struct
import json
import uuid
import time
import zlib
import hashlib
import numpy as np
from typing import Optional

# ── Try real SBERT, fall back to deterministic mock ──────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    _REAL_EMBEDDINGS = True
except ImportError:
    _REAL_EMBEDDINGS = False

MAGIC = b'CSFP'
VERSION = 0x0101   # 1.1 in MAJOR*256+MINOR form
HDC_DIM = 10_000
DEFAULT_PCA_K = 16
PROTOCOL_VERSION = "1.1.0"


def _mock_embed(texts: list[str], dim: int = 384) -> np.ndarray:
    """
    Deterministic mock embeddings when sentence-transformers not installed.
    Produces stable, distinct vectors per text using content hashing.
    Good enough for local demos; replace with real SBERT for production.
    """
    vectors = []
    for text in texts:
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        v = rng.randn(dim).astype(np.float32)
        v /= np.linalg.norm(v)
        vectors.append(v)
    return np.array(vectors)


def _embed(texts: list[str], model_name: str) -> tuple[np.ndarray, str]:
    """Embed texts, returning (matrix, model_name_used)."""
    if _REAL_EMBEDDINGS:
        model = SentenceTransformer(model_name)
        E = model.encode(texts, normalize_embeddings=True)
        return E.astype(np.float32), model_name
    else:
        return _mock_embed(texts), "mock-md5-384d"


def _hdc_fingerprint(compressed: np.ndarray, k: int, hdc_dim: int) -> np.ndarray:
    """
    CSP-1 normative HDC binding algorithm.
    Deterministic: same input always produces same fingerprint.
    """
    F = np.zeros(hdc_dim, dtype=np.float32)
    for i, z in enumerate(compressed):
        pos_rng = np.random.RandomState(i * 99991 + 7)
        pos_vec = pos_rng.randn(hdc_dim).astype(np.float32)
        pos_vec /= np.linalg.norm(pos_vec)

        proj_rng = np.random.RandomState(i * 31337 + k)
        proj = proj_rng.randn(k, hdc_dim).astype(np.float32) / np.sqrt(hdc_dim)

        msg_hdc = z.astype(np.float32) @ proj
        F += msg_hdc * pos_vec

    norm = np.linalg.norm(F)
    if norm > 0:
        F /= norm
    return F


def _pack_fp(
    hdc_vec: np.ndarray,
    pca_mean: np.ndarray,
    pca_components: np.ndarray,
    meta: dict,
) -> bytes:
    """Serialize everything into a .fp binary blob."""
    sec_hdc  = hdc_vec.astype(np.float32).tobytes()
    sec_pca  = (pca_mean.astype(np.float32).tobytes() +
                pca_components.astype(np.float32).tobytes())
    sec_meta = json.dumps(meta, ensure_ascii=False).encode("utf-8")

    sections = [(0x01, sec_hdc), (0x02, sec_pca), (0x03, sec_meta)]
    meta_json_bytes = sec_meta
    fp_id_bytes = uuid.UUID(meta["fp_id"]).bytes
    ts = meta["created_at"]

    # Section table + data blob
    sec_table = b""
    data_blob = b""
    base_offset = 80 + 2 + len(meta_json_bytes) + len(sections) * 16
    cur_offset = base_offset

    for sid, data in sections:
        sec_table += struct.pack("<BBIi6s", sid, 0, len(data), cur_offset, b"\x00" * 6)
        data_blob  += data
        cur_offset += len(data)

    header = (
        MAGIC
        + struct.pack("<H", VERSION)
        + struct.pack("<B", 0)           # flags
        + struct.pack("<B", 0)           # compression
        + struct.pack("<I", 0)           # total_len placeholder (patched below)
        + struct.pack("<I", 0)           # CRC placeholder
        + struct.pack("<H", len(sections))
        + struct.pack("<H", 0)           # reserved
        + b"\x00" * 32                   # content hash
        + fp_id_bytes
        + struct.pack("<q", ts)
        + struct.pack("<H", len(meta_json_bytes))
    )

    full = header + meta_json_bytes + sec_table + data_blob

    # Patch total_len at offset 8 with actual assembled size
    total_len = len(full)
    full = full[:8] + struct.pack("<I", total_len) + full[12:]

    # Patch CRC at offset 12
    crc  = zlib.crc32(full) & 0xFFFFFFFF
    full = full[:12] + struct.pack("<I", crc) + full[16:]
    return full


def encode_conversation(
    messages: list[dict],
    *,
    # v1.1 new fields
    task_type: str = "general",
    success_score: float = 0.0,
    task_tags: list[str] = None,
    task_description: str = "",
    # encoding config
    pca_k: int = DEFAULT_PCA_K,
    hdc_dim: int = HDC_DIM,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> bytes:
    """
    Encode a conversation list into a CSP-1 v1.1 .fp binary.

    messages: [{"role": "user"|"ai"|"assistant", "text": str}, ...]
    task_type: e.g. "pdf_extraction", "web_scraping", "code_generation"
    success_score: 0.0–1.0 (0 = failed, 1 = perfect)
    task_tags: ["pdf", "structured_data"]
    task_description: human-readable summary of the task
    """
    if not messages:
        raise ValueError("Cannot encode empty conversation")

    texts = [m["text"] for m in messages if m.get("text", "").strip()]
    if not texts:
        raise ValueError("No non-empty message texts found")

    # Embed
    E, model_used = _embed(texts, model_name)
    n, d = E.shape

    # PCA compression
    from sklearn.decomposition import PCA
    k = min(pca_k, n - 1, d)
    train_n = max(k + 1, int(n * 0.7))

    pca = PCA(n_components=k)
    pca.fit(E[:train_n])
    compressed = pca.transform(E)

    # HDC fingerprint
    F = _hdc_fingerprint(compressed, k, hdc_dim)

    # Build v1.1 metadata
    meta = {
        "csp_version": PROTOCOL_VERSION,
        "fp_id": str(uuid.uuid4()),
        "created_at": int(time.time() * 1000),
        "embedding_model": model_used,
        "embedding_dim": d,
        "pca_k": k,
        "hdc_dim": hdc_dim,
        "n_messages": n,
        "language": "en",
        "permitted_uses": ["style_generation", "identification"],
        # ── v1.1 additions ────────────────────────────────────────────────
        "task_type": task_type,
        "success_score": round(float(success_score), 4),
        "task_tags": task_tags or [],
        "task_description": task_description,
    }

    return _pack_fp(F, pca.mean_, pca.components_, meta)


def read_fp_meta(fp_bytes: bytes) -> dict:
    """Parse just the metadata from a .fp file (fast, no numpy)."""
    magic = fp_bytes[:4]
    if magic != MAGIC:
        raise ValueError(f"Not a .fp file (magic={magic})")
    meta_len = struct.unpack_from("<H", fp_bytes, 0x4C)[0]
    meta_json = fp_bytes[0x4E: 0x4E + meta_len].decode("utf-8")
    return json.loads(meta_json)


def read_fp_hdc(fp_bytes: bytes) -> np.ndarray:
    """Extract the HDC vector from a .fp file."""
    meta = read_fp_meta(fp_bytes)
    meta_len = struct.unpack_from("<H", fp_bytes, 0x4C)[0]
    n_sections = struct.unpack_from("<H", fp_bytes, 16)[0]
    sec_table_start = 0x4E + meta_len

    for i in range(n_sections):
        base = sec_table_start + i * 16
        sid    = fp_bytes[base]
        sec_len = struct.unpack_from("<I", fp_bytes, base + 2)[0]
        offset  = struct.unpack_from("<i", fp_bytes, base + 6)[0]
        if sid == 0x01:
            raw = fp_bytes[offset: offset + sec_len]
            return np.frombuffer(raw, dtype=np.float32).copy()

    raise ValueError("HDC_VECTOR section (0x01) not found")


def compare_fp(fp_bytes_a: bytes, fp_bytes_b: bytes) -> float:
    """Cosine similarity between two .fp fingerprints. Range [-1, 1]."""
    v1 = read_fp_hdc(fp_bytes_a)
    v2 = read_fp_hdc(fp_bytes_b)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10))


def merge_fp(fp_bytes_list: list[bytes], weights: list[float] = None) -> bytes:
    """
    Merge N fingerprints into one consensus fingerprint.
    Used by the registry to build 'best-practice' skill fingerprints.
    weights: if None, equal weighting.
    """
    if not fp_bytes_list:
        raise ValueError("Need at least one fingerprint to merge")

    hdcs = [read_fp_hdc(b) for b in fp_bytes_list]
    metas = [read_fp_meta(b) for b in fp_bytes_list]

    if weights is None:
        weights = [1.0] * len(hdcs)

    # Weighted average in HDC space
    F = np.zeros_like(hdcs[0])
    for hdc, w in zip(hdcs, weights):
        F += w * hdc
    norm = np.linalg.norm(F)
    if norm > 0:
        F /= norm

    # Merged metadata: inherit from first, note all source IDs
    base_meta = metas[0].copy()
    base_meta["fp_id"] = str(uuid.uuid4())
    base_meta["created_at"] = int(time.time() * 1000)
    base_meta["merged_from"] = [m["fp_id"] for m in metas]
    base_meta["n_messages"] = sum(m["n_messages"] for m in metas)
    base_meta["success_score"] = float(np.mean([m.get("success_score", 0) for m in metas]))
    base_meta["task_description"] = f"Consensus of {len(fp_bytes_list)} executions for '{base_meta.get('task_type','general')}'"

    # Reconstruct minimal PCA model from first fp for compatibility
    # (merge operates only on HDC space, PCA model from best performer)
    fp0_meta_len = struct.unpack_from("<H", fp_bytes_list[0], 0x4C)[0]
    n_sec = struct.unpack_from("<H", fp_bytes_list[0], 16)[0]
    sec_table_start = 0x4E + fp0_meta_len

    pca_mean = None
    pca_components = None

    for i in range(n_sec):
        base = sec_table_start + i * 16
        sid = fp_bytes_list[0][base]
        sec_len = struct.unpack_from("<I", fp_bytes_list[0], base + 2)[0]
        offset  = struct.unpack_from("<i", fp_bytes_list[0], base + 6)[0]
        if sid == 0x02:
            d = base_meta["embedding_dim"]
            k = base_meta["pca_k"]
            raw = fp_bytes_list[0][offset: offset + sec_len]
            pca_mean = np.frombuffer(raw[:d * 4], dtype=np.float32).copy()
            pca_components = np.frombuffer(raw[d * 4:], dtype=np.float32).reshape(k, d).copy()
            break

    return _pack_fp(F, pca_mean, pca_components, base_meta)
