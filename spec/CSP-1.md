# CSP-1: Conversational State Protocol, Version 2.0

**Status:** Draft
**License:** Apache 2.0
**Repository:** https://github.com/0xAshraFF/ConvoSeed
**Last updated:** March 2026

---

## Abstract

CSP-1 defines a portable, model-agnostic file format for encoding the communicative identity and skill knowledge of a human-AI conversation. A compliant `.fp` (fingerprint) file captures sufficient stylistic and contextual signal to reproduce conversational continuity on any conformant language model, without storing raw conversation data.

---

## 1. Motivation

Language model sessions are stateless. Each new conversation begins with no memory of prior interaction. Users who develop productive working relationships with AI systems — specific vocabulary, reasoning patterns, domain shortcuts — lose this context on every session reset.

CSP-1 addresses this as a **format problem**, not a storage problem. Rather than storing raw messages, it distills the essential signal into a compact, portable, user-owned file.

---

## 2. Definitions

The key words "MUST", "MUST NOT", "REQUIRED", "SHOULD", "SHOULD NOT", "MAY" in this document are to be interpreted as described in RFC 2119.

- **Fingerprint (.fp file):** A ZIP archive conforming to this specification
- **Identity fingerprint:** A `.fp` file encoding a user's communicative style
- **Skill fingerprint:** A `.fp` file encoding task-specific procedural knowledge
- **Combined fingerprint:** A `.fp` file encoding both identity and skill
- **Injection:** The act of prepending `summary.txt` content to a system prompt
- **Cold transfer:** Using a fingerprint on a model it was not generated from

---

## 3. File Format

### 3.1 Container

A `.fp` file MUST be a valid ZIP archive (PKZip format, any compression level).

The archive MUST contain the following files:

| File | Required | Description |
|------|----------|-------------|
| `manifest.json` | REQUIRED | Protocol metadata and scores |
| `summary.txt` | REQUIRED | Human-readable style/skill description |
| `metadata.json` | REQUIRED | Generation provenance |
| `vector.bin` | OPTIONAL | HDC-encoded retrieval vector |
| `examples/` | OPTIONAL | Directory of example message pairs |

Total archive size SHOULD NOT exceed 200KB.

### 3.2 manifest.json

MUST be valid JSON. MUST contain the following fields:
```json
{
  "csp_version": "2.0",
  "fp_type": "identity | skill | combined",
  "task_type": "string | null",
  "success_score": "float 0.0–1.0 | null",
  "created_at": "ISO 8601 timestamp",
  "model_origin": "string"
}
```

- `csp_version` MUST be `"2.0"` for files conforming to this specification
- `fp_type` MUST be one of `"identity"`, `"skill"`, or `"combined"`
- `task_type` SHOULD describe the domain for skill fingerprints (e.g. `"sentiment_analysis"`)
- `success_score` SHOULD be the empirical task success rate if measured, otherwise `null`
- `model_origin` SHOULD identify the model used to generate the fingerprint (e.g. `"claude-sonnet-4-6"`)

### 3.3 summary.txt

MUST be a plain UTF-8 text file.
MUST be between 60 and 200 words.
MUST describe the communicative style, vocabulary, reasoning patterns, or task approach being encoded.
MUST NOT contain raw conversation messages.
MUST NOT contain personally identifiable information beyond stylistic description.

The summary is the primary performance mechanism. Implementations SHOULD invest in summary quality.

### 3.4 metadata.json

MUST be valid JSON. MUST contain:
```json
{
  "generated_at": "ISO 8601 timestamp",
  "model_origin": "string",
  "source_message_count": "integer | null",
  "summary_token_count": "integer",
  "vector_dimensions": "integer | null"
}
```

### 3.5 vector.bin (optional)

If present, MUST be a binary file containing a float16 numpy array of shape `(D,)` where D is the HDC vector dimensionality (RECOMMENDED: 10,000).

The vector is intended for similarity retrieval and speaker identification only. It MUST NOT be used as a generation mechanism.

---

## 4. Injection Protocol

### 4.1 Basic Injection

To apply a fingerprint, a conformant implementation MUST prepend the contents of `summary.txt` to the system prompt:

```
system_prompt = summary.txt_content + "\n\n" + original_system_prompt
```

### 4.2 Multiple Fingerprints

When injecting multiple fingerprints (e.g. identity + skill), implementations SHOULD concatenate summaries in this order:

1. Identity fingerprint summary
2. Skill fingerprint summary
3. Original system prompt

### 4.3 Cold Transfer

A fingerprint generated on one model MUST be injectable into any other conformant model without modification. This is the portability guarantee of CSP-1.

Validated cold transfers as of v2.0:
- Claude Sonnet 4.6 → GPT-4o
- Claude Sonnet 4.6 → Gemini 1.5 Flash

---

## 5. Fingerprint Types

### 5.1 Identity Fingerprint (`fp_type: "identity"`)

Encodes how a person communicates: vocabulary, sentence structure, reasoning style, tone, formatting preferences. Used to preserve conversational continuity across sessions.

### 5.2 Skill Fingerprint (`fp_type: "skill"`)

Encodes task-specific procedural knowledge: how to approach a class of problems, what edge cases to watch for, what output format to use. Used to cache domain expertise.

### 5.3 Combined Fingerprint (`fp_type: "combined"`)

Encodes both. The `summary.txt` SHOULD clearly separate identity and skill sections.

---

## 6. Generation

CSP-1 does not mandate a specific generation method. The reference implementation uses:

1. Select representative message samples from the conversation
2. Prompt a capable LLM to produce a stylistic description
3. Validate length (60–200 words)
4. Package into ZIP archive with manifest and metadata

Reference implementation: `tools/fp_create.py`

---

## 7. Registry (Optional)

Implementations MAY maintain a local registry at `~/.convoseed/registry.db` (SQLite).
```sql
CREATE TABLE fingerprints (
  id TEXT PRIMARY KEY,
  fp_type TEXT,
  task_type TEXT,
  summary TEXT,
  success_score REAL,
  model_origin TEXT,
  created_at TEXT,
  path TEXT
);
```

---

## 8. Security Considerations

- `.fp` files MUST NOT contain raw API keys, passwords, or credentials
- `.fp` files SHOULD NOT contain raw conversation messages
- Implementations MUST NOT transmit `.fp` files to third parties without explicit user consent
- The user owns their `.fp` files. Platforms implementing CSP-1 MUST NOT claim ownership of user fingerprints.

---

## 9. Validation

A conformant `.fp` file MUST pass the following checks:

1. Is a valid ZIP archive
2. Contains `manifest.json`, `summary.txt`, `metadata.json`
3. `manifest.json` parses as valid JSON with all required fields
4. `csp_version` is `"2.0"`
5. `summary.txt` is UTF-8, between 60 and 200 words
6. Total archive size ≤ 200KB

---

## 10. Relation to Other Protocols

| Protocol | Layer | Covers |
|----------|-------|--------|
| DID (W3C) | Identity | Who the user IS cryptographically |
| MCP (Anthropic) | Tooling | What tools the agent can ACCESS |
| **CSP-1** | **Cognition** | **How the user SPEAKS and THINKS** |

---

## 11. Versioning

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.0 | February 2026 | Initial spec, HDC binary encoder |
| v2.0 | March 2026 | Text summary as primary mechanism, cold transfer validated, Apache 2.0 |

---

## 12. Contributing

Open challenges:
- Cross-model skill fingerprint transfer (V3 portability)
- HDC vector decoding to text
- Fingerprint merging for multi-session consensus
- Formal composition rules for conversations > 500 messages

---

*"AI memory is a format problem, not a storage problem."*
