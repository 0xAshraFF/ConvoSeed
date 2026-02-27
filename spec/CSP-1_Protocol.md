# CSP-1: Conversational Style Protocol
## Binary Specification — v0.2 — February 2026

---

### Overview

CSP-1 defines the `.fp` (fingerprint) binary file format for encoding the
stylistic and semantic essence of a human-AI conversation into a portable,
fixed-size, user-owned file.

**Core invariant:** `|fp| ≈ 200KB` regardless of conversation length N.

**Privacy invariant:** No message in corpus M is recoverable from the `.fp` file.

---

### File Layout

```
Offset    Section       Size      Type        Description
──────────────────────────────────────────────────────────────────────
0x00      MAGIC         4 bytes   Fixed       0x43 0x53 0x50 0x31 ("CSP1")
0x04      VERSION       2 bytes   uint16      0x0002 (v0.2)
0x06      FLAGS         2 bytes   bitmask     See FLAGS below
0x08      TIMESTAMP     8 bytes   uint64      Unix epoch (ms) of encoding
0x10      CRC32         4 bytes   uint32      CRC-32 of everything after offset 0x14
0x14      SECTION_MAP   64 bytes  Fixed       Offsets + sizes for each section
──────────────────────────────────────────────────────────────────────
          HEADER ends at 0x54 (~84 bytes)

Section   Offset        Size (typ)  Description
──────────────────────────────────────────────────────────────────────
PCA_MODEL SECTION_MAP.pca_offset   ~8 KB   Style centroid (see below)
HDC_SEED  SECTION_MAP.hdc_offset   ~140 KB Hypervector (float16, 10000-dim)
PREFIX    SECTION_MAP.pfx_offset   ~40 KB  Prefix tuning tensor
SIGNATURE SECTION_MAP.sig_offset   ~1 KB   Ed25519 signature + public key
CHUNKS    SECTION_MAP.chk_offset   ~10 KB  Chunked index (optional)
```

---

### FLAGS Bitmask

```
Bit 0  HAS_PREFIX    Prefix tuning tensor is present
Bit 1  HAS_CHUNKS    CHUNKS section is present
Bit 2  IS_SIGNED     Ed25519 signature is present
Bit 3  COMPRESSED    HDC_SEED is gzip-compressed (future)
Bit 4–15             Reserved, must be 0
```

---

### PCA_MODEL Section

Encodes the style centroid of the conversation.

```
Field         Type            Size          Description
──────────────────────────────────────────────────────────────────────
EMBED_DIM     uint16          2 bytes       Embedding dimension (e.g. 384)
N_COMPONENTS  uint16          2 bytes       Number of PCA components stored
N_MESSAGES    uint32          4 bytes       Number of messages encoded
MEAN_VEC      float32[]       EMBED_DIM × 4 Style mean vector μ
COMPONENTS    float32[]       N_COMPONENTS × EMBED_DIM × 4   Eigenvectors W
```

**Note:** Full components (N_COMPONENTS = min(N, EMBED_DIM)) are stored
for lossless reconstruction. Identification requires only k=4 components
but all are retained for future use.

---

### HDC_SEED Section

The temporal hypervector binding of the conversation sequence.

```
Field         Type            Size          Description
──────────────────────────────────────────────────────────────────────
HDC_DIM       uint32          4 bytes       Hypervector dimension (10000)
ENCODING      uint8           1 byte        0x01 = float16, 0x02 = binary
SEED_VEC      float16[]       HDC_DIM × 2   The bound hypervector (~20 KB)
PROJ_SEED     uint64          8 bytes       Random seed for projection matrix R
```

**Encoding:** Each message vector v_i is projected via R ∈ R^(k × D), sign-binarised,
then bound using cyclic-shift XOR: `seed = ρ^(N-1)(h1) ⊕ ... ⊕ hN`

**Collision probability:** P[cos(u,v) > 0.1] ≈ 0.01% in 10,000-dim space.

---

### PREFIX Section

Prefix tuning tensor for conditioned language model generation.

```
Field         Type            Size          Description
──────────────────────────────────────────────────────────────────────
MODEL_ID      uint8[64]       64 bytes      Null-terminated model identifier
              (e.g. "gemma3:12b", "gpt2", "claude-3")
PREFIX_LEN    uint16          2 bytes       Number of prefix tokens P
HIDDEN_DIM    uint32          4 bytes       Model hidden dimension d_model
PREFIX_TENSOR float16[]       P × d_model × 2   Soft token embeddings
```

**Note:** The PREFIX section is model-specific. The same `.fp` file may contain
multiple PREFIX sections for different target models (future: v0.3).
The HDC_SEED is model-agnostic and can generate a new PREFIX for any model.

---

### SIGNATURE Section

Ed25519 cryptographic ownership proof.

```
Field         Type            Size          Description
──────────────────────────────────────────────────────────────────────
ALG           uint8           1 byte        0x01 = Ed25519
PUBLIC_KEY    bytes[32]       32 bytes      Ed25519 public key
SIGNATURE     bytes[64]       64 bytes      Signature over SIGNED_CONTENT
CONSENT       uint8[256]      256 bytes     Machine-readable consent flags (JSON, null-padded)
```

**SIGNED_CONTENT:** SHA-256(PCA_MODEL_bytes || HDC_SEED_bytes || PREFIX_bytes)

**CONSENT field (JSON schema):**
```json
{
  "commercial": true,
  "therapy": false,
  "legacy": false,
  "expires": "2027-01-01",
  "platforms": ["*"],
  "revoked": false
}
```

---

### CHUNKS Section

Enables scalability for conversations exceeding 500 messages.

```
Field         Type            Size          Description
──────────────────────────────────────────────────────────────────────
N_CHUNKS      uint16          2 bytes       Number of chunks
CHUNK_SIZE    uint16          2 bytes       Messages per chunk (e.g. 50)
CHUNK_INDEX   ChunkRecord[]   N_CHUNKS × 28 Per-chunk metadata
GLOBAL_SEED   float16[10000]  20 KB         Global hypervector (all chunks bound)
```

**ChunkRecord (28 bytes):**
```
MSG_START   uint32    First message index in this chunk
MSG_END     uint32    Last message index in this chunk
TIMESTAMP   uint64    Unix epoch of chunk creation
CHUNK_SEED  float16[10000] → stored as offset + reference, not inline
```

**Composition rule (v0.2):** Global seed = majority-bind of all chunk seeds.
Chunks are quasi-orthogonal; binding preserves global style while allowing
incremental updates without re-encoding from scratch.

**Open challenge:** Formal proof of style preservation under composition
for N_CHUNKS > 10 is an active research question (see CONTRIBUTING.md).

---

### Core Operations

#### encode(messages) → .fp
```python
def encode(messages: list[str], model_id: str, privkey: bytes) -> FingerprintFile:
    vecs = sbert.encode(messages)                    # (N, 384)
    pca = PCA(n_components=None).fit(vecs)           # lossless
    projected = pca.transform(vecs)                  # (N, k)
    seed = hdc_bind_sequence(projected, dim=10_000)  # (10000,)
    prefix = train_prefix(seed, model_id)            # (P, d_model)
    sig = ed25519_sign(pca, seed, prefix, privkey)
    return FingerprintFile(pca, seed, prefix, sig)
```

#### identify(query, candidates) → fp_id
```python
def identify(query: str, candidates: dict[str, FingerprintFile]) -> str:
    q_vec = sbert.encode([query])[0]
    q_proj = candidates[0].pca.transform([q_vec])
    q_hv = hdc_encode(q_proj)
    scores = {fid: cosine(q_hv, fp.hdc_seed) for fid, fp in candidates.items()}
    return max(scores, key=scores.get)
```

#### generate(fp, prompt) → str
```python
def generate(fp: FingerprintFile, prompt: str, model) -> str:
    prefix_tokens = fp.get_prefix(model.id)         # retrieve or compute
    return model.generate(prefix=prefix_tokens, prompt=prompt)
```

---

### Versioning

| Version | Key Changes |
|---|---|
| v0.1 | Initial release. PCA + HDC + SIGNATURE. 63KB. |
| v0.2 | Added PREFIX section. Added CHUNKS section. Updated to 200KB. Model ID field. CONSENT JSON in SIGNATURE. |
| v0.3 (planned) | Multi-PREFIX support. Cross-model mapping API. |

---

### Privacy Guarantees

- **No raw message recovery:** PCA centroid is a statistical aggregate. No individual message is recoverable.
- **No content leakage:** SBERT embeddings are not invertible to the original text.
- **Ownership proof:** Ed25519 signature prevents impersonation without the private key.
- **Consent machine-readable:** The CONSENT field enables platforms to programmatically check usage permissions.
- **GDPR alignment:** Style without content = privacy by design.

---

### Reference Implementation

See `/src/` for Python reference implementation.
See `/experiments/gemma3_12b_results.json` for validation data.

---

*CSP-1 v0.2 — ConvoSeed — MIT Licence — github.com/yourusername/ConvoSeed*
