# convoseed-agent

**Compress any conversation into a portable 200KB `.fp` fingerprint file.**

ConvoSeed implements the CSP-1 protocol — a method for encoding the *style* of a conversation (not the content) using SBERT embeddings, PCA compression, and Hyperdimensional Computing. The result is a fixed-size file you own and can load into any AI session.

```
pip install convoseed-agent
```

---

## 5-minute demo

**Step 1 — install**
```bash
pip install convoseed-agent
pip install sentence-transformers scikit-learn numpy
```

**Step 2 — encode a conversation**

Your conversation must be a JSON file in this format:
```json
[
    {"role": "user", "content": "I've been thinking about memory..."},
    {"role": "assistant", "content": "Memory is deeply selective..."},
    ...
]
```

Then run:
```bash
convoseed-encode --input my_conversation.json --output identity.fp
```

Or in Python:
```python
import json
from convoseed_agent import encode_conversation

with open("my_conversation.json") as f:
    messages = json.load(f)

encode_conversation(messages, "identity.fp")
# → identity.fp  (~200KB, fixed size regardless of conversation length)
```

**Step 3 — identify a speaker from a new message**
```python
from convoseed_agent import identify, load_fp
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

winner, scores = identify(
    query_text="I wonder if that cognitive style could be captured somehow",
    fp_paths=["identity.fp", "other_person.fp"],
    model=model
)

print(f"Best match: {winner}")
for path, score in sorted(scores.items(), key=lambda x: -x[1]):
    print(f"  {score:.4f}  {path}")
```

---

## What it does

```
Messages → SBERT embed → PCA compress → HDC bind → .fp file
```

1. **Embed** — Sentence-BERT encodes each message into a 384-dim vector
2. **Compress** — PCA extracts the style centroid (4 components = full accuracy)
3. **Bind** — Hyperdimensional Computing (10,000-dim) weaves temporal sequence into one vector
4. **Save** — Written to a portable JSON-based `.fp` file (~200KB)

Key result from the research paper: **4 PCA components capture full speaker identification accuracy**, meaning conversational style is genuinely low-dimensional. You can represent how someone thinks with 4 numbers.

---

## Research results

Validated on a real 524-message researcher-AI conversation:

| Model | Avg Similarity | Peak | Msgs > 0.7 |
|---|---|---|---|
| GPT-2 (124M) | 0.464 | 1.000 | 1 |
| Gemma3:1b | 0.466 | 0.707 | 1 |
| **Gemma3:12b** | **0.523** | **0.757** | **4** |

Speaker identification: **52% accuracy** on 10 candidates (vs 10% random baseline), p < 10⁻¹⁰⁰.

---

## Optional: generation (requires torch)

```bash
pip install convoseed-agent[decode]
```

```python
from convoseed_agent import generate_with_prefix, load_fp

fp = load_fp("identity.fp")
output = generate_with_prefix("Tell me about your weekend", fp, model_name="gpt2")
print(output)
```

---

## Status

Early research. Proof-of-concept validated on real data. Open for collaboration.

- [x] CSP-1 protocol specification
- [x] Encoder / decoder / identifier
- [x] Speaker identification experiment (1,000 trials)
- [x] Multi-model validation
- [ ] Cross-model mapping (open research problem)
- [ ] Public fingerprint registry

---

## Links

- GitHub: https://github.com/0xAshraFF/ConvoSeed
- Protocol spec: `/spec/CSP-1.md` in the repo
- Research paper: `/docs/` in the repo

MIT License.
