# CSP-1 — Conversational Style Protocol, Version 1.1.0

**Status:** Active  
**Version:** 1.1.0  
**Previous version:** 0.2  
**Date:** February 2026  
**Author:** Ashraful (0xAshraFF)  
**Repository:** https://github.com/0xAshraFF/ConvoSeed

---

## Changelog: v0.2 → v1.1.0

This is a **MINOR** version bump. All v0.2 `.fp` files remain valid — the four
new metadata fields are optional. Implementations that do not set them default
to empty/zero values.

| Field added | Type | Default | Purpose |
|---|---|---|---|
| `task_type` | `string` | `"general"` | Groups fingerprints by task category |
| `success_score` | `float [0.0–1.0]` | `0.0` | Quality signal for merge weighting |
| `task_tags` | `string[]` | `[]` | Free-form labels for search/filter |
| `task_description` | `string` | `""` | Human-readable summary of the task |

**Why these fields matter:** They are what transform a ConvoSeed fingerprint
from a personal identity artifact into an **agent skill cache entry**. Without
`task_type`, fingerprints cannot be grouped for merging. Without `success_score`,
the merge operation has no quality signal. Together, they enable the nightly
consensus merge that makes every future agent session start warm.

---

## 1. Overview

CSP-1 defines a binary file format (`.fp`) and a set of operations for encoding,
storing, comparing, and merging conversational style fingerprints.

A `.fp` file captures **how** a conversation was conducted — the reasoning style,
vocabulary, semantic structure, and problem-solving approach — compressed into a
fixed-size binary artifact. It does **not** store raw message content.

CSP-1 is the **third leg** of the emerging agent identity stack:

| Layer | Covers | Status |
|---|---|---|
| DID (W3C) | Who the user IS cryptographically | Specified |
| MCP (Anthropic) | What tools the agent can ACCESS | Specified |
| **CSP-1** | **How the user SPEAKS and THINKS** | **This work** |

---

## 2. File Format

### 2.1 Magic and Header

Every `.fp` file begins with a fixed 80-byte header:

```
Offset  Size  Field
------  ----  -----
0x00    4     Magic bytes: 0x43 0x53 0x46 0x50  ("CSFP")
0x04    2     Version: 0x0101  (MAJOR=1, MINOR=1)
0x06    1     Flags (reserved, set to 0)
0x07    1     Compression (0 = none)
0x08    4     Total file length in bytes (uint32 LE)
0x0C    4     CRC-32 of entire file (with this field zeroed during compute)
0x10    2     Number of sections (uint16 LE)
0x12    2     Reserved (set to 0)
0x14    32    Content hash (SHA-256, reserved for future use, zeroed)
0x34    16    Fingerprint UUID (fp_id, bytes)
0x44    8     Creation timestamp (Unix ms, int64 LE)
0x4C    2     Length of META_JSON section in bytes (uint16 LE)
0x4E    ...   META_JSON bytes (UTF-8 encoded JSON, length from above)
```

### 2.2 Section Table

Immediately after META_JSON, a section table lists all data sections:

```
Each entry is 16 bytes:
  Offset  Size  Field
  ------  ----  -----
  +0      1     Section ID (uint8)
  +1      1     Reserved
  +2      4     Section length in bytes (uint32 LE)
  +6      4     Absolute offset in file (int32 LE)
  +10     6     Reserved (zero)
```

**Section IDs:**

| ID | Name | Description |
|---|---|---|
| `0x01` | HDC_VECTOR | 10,000-dim float32 hypervector, unit normalised |
| `0x02` | PCA_MODEL | PCA mean (384 floats) + components (k×384 floats) |
| `0x03` | META_JSON | Duplicate of header metadata as JSON (for easy reading) |

### 2.3 META_JSON Schema

The metadata block is a UTF-8 JSON object. All fields from v0.2 are preserved.
**Bold fields are new in v1.1.**

```json
{
  "csp_version":      "1.1.0",
  "fp_id":            "<uuid4>",
  "created_at":       1234567890000,
  "embedding_model":  "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_dim":    384,
  "pca_k":            16,
  "hdc_dim":          10000,
  "n_messages":       4,
  "language":         "en",
  "permitted_uses":   ["style_generation", "identification"],

  "task_type":        "pdf_extraction",
  "success_score":    0.9200,
  "task_tags":        ["pdf", "finance", "tables"],
  "task_description": "Extract quarterly earnings tables from annual report"
}
```

#### Field reference

| Field | Type | v0.2 | v1.1 | Description |
|---|---|---|---|---|
| `csp_version` | string | ✓ | ✓ | Semantic version of the protocol |
| `fp_id` | string (UUID4) | ✓ | ✓ | Unique identifier for this fingerprint |
| `created_at` | int (Unix ms) | ✓ | ✓ | Creation timestamp |
| `embedding_model` | string | ✓ | ✓ | SBERT model used for encoding |
| `embedding_dim` | int | ✓ | ✓ | Embedding vector dimension (typically 384) |
| `pca_k` | int | ✓ | ✓ | Number of PCA components used (4–32, default 16) |
| `hdc_dim` | int | ✓ | ✓ | HDC hypervector dimension (default 10,000) |
| `n_messages` | int | ✓ | ✓ | Number of messages encoded |
| `language` | string | ✓ | ✓ | ISO 639-1 language code |
| `permitted_uses` | string[] | ✓ | ✓ | Allowed uses of this fingerprint |
| **`task_type`** | string | — | ✓ | Task category e.g. `"pdf_extraction"` |
| **`success_score`** | float [0,1] | — | ✓ | Quality rating of this session |
| **`task_tags`** | string[] | — | ✓ | Free-form tags for search |
| **`task_description`** | string | — | ✓ | Human-readable task summary |

**Merge-only fields** (present when `merged_from` is set):

| Field | Type | Description |
|---|---|---|
| `merged_from` | string[] | List of `fp_id` values that were merged |

---

## 3. Encoding Algorithm

### 3.1 Pipeline

```
messages → SBERT embed → PCA compress → HDC bind → pack → .fp
```

1. **Embed** — Each message text is encoded with Sentence-BERT into a
   384-dimensional float32 vector, L2-normalised.

2. **Compress** — PCA is fit on 70% of messages (train split), then
   all messages are projected to `k` components (default k=16).
   Key finding: accuracy is invariant to k across range 4–32.

3. **Bind** — The HDC fingerprinting algorithm (section 3.2) folds the
   compressed sequence into one 10,000-dimensional unit vector.

4. **Pack** — The HDC vector, PCA model, and metadata are serialised
   into the binary format (section 2).

### 3.2 HDC Binding Algorithm (Normative)

This algorithm is **normative** — all compliant implementations must
produce identical output for identical input. The seeds are fixed.

```python
F = zeros(hdc_dim)

for i, compressed_msg in enumerate(compressed_messages):
    # Position vector — deterministic from index
    pos_rng = RandomState(seed = i * 99991 + 7)
    pos_vec = pos_rng.randn(hdc_dim)
    pos_vec /= norm(pos_vec)

    # Projection matrix — deterministic from index and k
    proj_rng = RandomState(seed = i * 31337 + k)
    proj = proj_rng.randn(k, hdc_dim) / sqrt(hdc_dim)

    # Bind position and content
    F += (compressed_msg @ proj) * pos_vec

F /= norm(F)   # Normalise to unit sphere
```

**Seeds must be exact.** Any deviation breaks portability between implementations.

---

## 4. Core Operations

### 4.1 `encode(messages) → .fp`

Compress a conversation into a fingerprint file. v1.1 signature:

```python
encode_conversation(
    messages: list[dict],       # [{"role": str, "text": str}, ...]
    task_type: str = "general",
    success_score: float = 0.0,
    task_tags: list[str] = [],
    task_description: str = "",
    pca_k: int = 16,
    hdc_dim: int = 10_000,
) -> bytes
```

### 4.2 `decode(.fp) → embeddings`

Reconstruct approximate embeddings from a stored fingerprint.
Used for style-conditioned generation.

### 4.3 `condition(.fp, model) → prefix`

Project a fingerprint into an LLM's prefix embedding space.
The returned prefix conditions the model to respond in the
encoded style. This is the operation used by `SkillCache`.

### 4.4 `compare(fp_a, fp_b) → float`

Cosine similarity between two fingerprint HDC vectors.
Range: [-1.0, 1.0]. Identical fingerprints return 1.0.

```python
similarity = dot(hdc_a, hdc_b) / (norm(hdc_a) * norm(hdc_b))
```

### 4.5 `merge([fp_1 … fp_N], weights) → .fp`  *(v1.1 extended)*

Weighted average of N fingerprints in HDC space, normalised.
Used by the registry to build consensus skill fingerprints.

```python
F_merged = normalise( Σ weight_i × hdc_i )
```

**v1.1 merge behaviour:**
- `success_score` in merged file = mean of input scores
- `merged_from` field lists all source `fp_id` values
- `task_description` auto-set to `"Consensus of N executions for '{task_type}'"`
- PCA model inherited from highest-scoring source fingerprint

---

## 5. Agent Skill Cache (v1.1 Use Case)

The four new metadata fields enable a complete agent skill caching loop.
This was not possible with v0.2.

### 5.1 The Loop

```
Session completes
  → encode to .fp  (task_type + success_score set)
  → write to sessions directory

Nightly scheduler runs
  → group .fp files by task_type
  → select top-N by success_score
  → merge() → consensus .fp
  → write to registry/consensus/

New session starts
  → query registry for task_type
  → load consensus .fp as conditioning prefix
  → agent starts warm, inheriting best-practice reasoning
```

### 5.2 `ConvoSeedSession` (Reference Implementation)

```python
from convoseed_agent import ConvoSeedSession

with ConvoSeedSession(
    task_type="pdf_extraction",
    task_tags=["pdf", "finance"],
    success_score=0.94,
) as session:
    session.add_message("user", "Extract the tables from this PDF.")
    session.add_message("assistant", "Found 3 tables. Outputting as JSON.")

# → ~/.convoseed/sessions/pdf_extraction_20260228_143022_019ms.fp
```

### 5.3 `SkillCache` (Reference Implementation)

```python
from convoseed_agent import SkillCache

cache = SkillCache()
prefix = cache.get_prefix("pdf_extraction")

if prefix:
    system_prompt = prefix.as_system_prompt()
    # Inject into LLM call as system message
```

---

## 6. Versioning Policy

CSP-1 follows semantic versioning: `MAJOR.MINOR.PATCH`

| Change type | Version bump | Example |
|---|---|---|
| New optional metadata fields | MINOR | v0.2 → v1.1 |
| Breaking change to binary layout | MAJOR | v1.x → v2.0 |
| Bug fix with no format change | PATCH | v1.1.0 → v1.1.1 |

**Backward compatibility guarantee:** A v1.1 implementation can read all v0.2
`.fp` files. Missing v1.1 fields default to empty/zero values.

---

## 7. Security

- Fingerprints do not contain raw message text
- `fp_id` is a UUID4 — not derived from content
- CRC-32 detects accidental corruption (not adversarial tampering)
- `permitted_uses` field signals intent; enforcement is application-level
- For cryptographic ownership proof, see the SIGNATURE section in the
  full binary spec (Ed25519, documented separately)

---

## 8. Open Challenges

1. **Cross-Model Mapping** — translating a `.fp` fingerprint encoded with
   SBERT into GPT-4 or other backbone embedding spaces without re-encoding
   the original conversation.

2. **CHUNKS Scaling** — formal composition rules for threads exceeding 500
   messages while preserving the fixed file size.

3. **Incentive Design** — what makes AI platforms adopt an open standard
   that reduces their own lock-in?

Contributions welcome — open an Issue on GitHub.

---

## 9. Reference Implementation

```
pip install convoseed-agent
```

Source: `src/convoseed_agent/` in this repository.

Modules:

| Module | Implements |
|---|---|
| `encoder.py` | Sections 3, 4.1, 4.4, 4.5 |
| `wrapper.py` | Section 5.2 (ConvoSeedSession) |
| `registry.py` | Section 5.1 (index, query, merge scheduler) |
| `cache.py` | Section 5.3 (SkillCache) |
| `scheduler.py` | Section 5.1 (nightly merge daemon) |

---

*"Style is the invariant that survives compression."*  
CSP-1 v1.1.0 · MIT License · Open forever.
