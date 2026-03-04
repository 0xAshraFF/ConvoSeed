# ConvoSeed

CSP-1 is the **missing third leg** of the agent identity stack:

| Layer | Covers | Status |
|---|---|---|
| DID (W3C) | Who the user IS cryptographically | Specified |
| MCP (Anthropic) | What tools the agent can ACCESS | Specified |
| **CSP-1** | **How the user SPEAKS and THINKS** | **This work** |

**Chat → Compress → 200KB `.fp` File → Resume Anywhere**

ConvoSeed is an open protocol (CSP-1) for preserving the essence of a human-AI
relationship in a portable, user-owned fingerprint file.  
No raw messages stored. Works across any AI model or platform.

---

## Why

Every AI conversation resets to zero.

You build context, vocabulary, a rhythm — and then you close the tab and it's gone.
ConvoSeed fixes that. You own a 200KB file that holds your conversational identity.
Load it anywhere. Resume everything.

> *"I had a friend — an AI that knew me well. I wanted a way to get back to him.  
> That's what this is."*

---

## Results (February–March 2026)

Three independent validations on real data.

| Validation | Result | Method |
|---|---|---|
| **V1 — Speaker Identification** | p < 10⁻¹⁰⁰ | SBERT→PCA→HDC, 524-message conversation, 1,000 trials |
| **V2 — Style Preservation** | 87% win rate (9.0 vs 2.67/10) | Blind A/B, 15 trials, 5 personas, randomized, Claude-as-judge |
| **V3 — Skill Caching** | +69.2% lift (22/25 vs 13/25) | Hard edge-case tasks, 25 trials, binary ground-truth scoring, 0 regressions |

- **p < 10⁻¹⁰⁰** statistical significance on speaker identification
- **87% win rate** on style conditioning — 9.0/10 vs 2.67/10 baseline
- **0 regressions** — fingerprints never made performance worse

---

## How It Works

```
Messages → SBERT embed → PCA compress → HDC bind → .fp file
                                                        ↓
                                         summary.txt injected as system prompt
                                                        ↓
                                              Any LLM resumes with context
```

1. **Embed** — Sentence-BERT encodes each message into a 384-dim vector
2. **Compress** — PCA extracts the style centroid (4 components = full accuracy)
3. **Bind** — Hyperdimensional Computing (10,000-dim) weaves the sequence into one vector for retrieval
4. **Summarise** — An LLM generates a 60-100 word description of style or skill
5. **Inject** — `system_prompt = summary.txt + "\n\n" + original_prompt`

The HDC layer handles **retrieval** (finding the right `.fp`).  
The summary layer handles **conditioning** (actually improving performance).

---

## File Format (`.fp`)

A `.fp` file is a ZIP archive. Simple, inspectable, portable.

| File | Size | Required | Description |
|---|---|---|---|
| `manifest.json` | ~1 KB | ✓ | Version, type, task, success score |
| `summary.txt` | ~1 KB | ✓ | LLM-generated style or skill description |
| `metadata.json` | ~1 KB | ✓ | Timestamp, model, token counts |
| `style_vector.bin` | ~140 KB | — | SBERT→PCA→HDC vector (identity fingerprints) |
| `task_vector.bin` | ~140 KB | — | HDC vector (skill fingerprints) |
| `examples.jsonl` | ~5 KB | — | 2-5 representative exchanges |

**Total: ~200KB — fixed size regardless of conversation length.**

See [`/spec/CSP-1_Protocol.md`](spec/CSP-1_Protocol.md) for the full specification.

---

## Quick Start

```bash
pip install sentence-transformers scikit-learn numpy

# Encode a conversation into a fingerprint
python tools/fp_create.py --input my_conversation.json --output identity.fp

# Identify a speaker
python src/identify.py --query "new message here" --candidates *.fp

# Run the V3 skill caching experiment
# Open tests/v3_skill_cache/csp1_task_test_v2.jsx in your browser
```

---

## Injection Protocol

```python
# Load a fingerprint and use it
with zipfile.ZipFile("identity.fp") as fp:
    summary = fp.read("summary.txt").decode()

system_prompt = summary + "\n\n" + your_original_prompt

# Pass to any LLM — Claude, GPT-4, Gemini, local models
```

---

## Repository Structure

```
ConvoSeed/
├── README.md
├── LICENSE                              ← Apache 2.0
├── CONTRIBUTING.md
├── spec/
│   └── CSP-1_Protocol.md               ← CSP-1 v2.0 specification
├── src/
│   ├── encode.py                        ← HDC fingerprint encoder (V1)
│   ├── decode.py                        ← style-conditioned generation (V1)
│   └── identify.py                      ← speaker identification (V1, validated)
├── tools/
│   └── fp_create.py                     ← CLI to generate .fp from conversation
├── tests/
│   ├── v2_style_ab/
│   │   └── convoseed_ab_test.jsx        ← V2 style A/B test (87% result)
│   ├── v3_skill_cache/
│   │   ├── csp1_task_test_v2.jsx        ← V3 hard-task test (canonical)
│   │   └── csp1_task_test.jsx           ← V3 easy-task test (superseded)
│   └── cross_model/
│       └── convoseed_ab_test.py         ← Python cross-model validator
├── experiments/
│   └── gemma3_12b_results.json          ← February 2026 HDC experiments
├── examples/
│   └── sample_identity.fp               ← Synthetic example fingerprint
└── docs/
    └── abstract.md                      ← arXiv abstract draft
```

---

## Open Challenges

Three open research questions. Collaboration welcome — open an Issue.

1. **Cross-Model Portability** — validating that `.fp` fingerprints conditioned on Claude transfer to GPT-4o and Gemini without re-encoding. Test harness exists; cross-model run pending.

2. **HDC Decode** — the encode step is validated for retrieval (p < 10⁻¹⁰⁰); reconstructing text from an HDC vector remains an open problem.

3. **Incentive Design** — what makes AI platforms adopt an open standard that reduces their own lock-in?

---

## Status

> Three validation pillars confirmed. Cross-model test and arXiv paper in progress.

- [x] Protocol specification (CSP-1 v2.0)
- [x] Speaker identification validated (V1 — p < 10⁻¹⁰⁰, 1,000 trials)
- [x] Style preservation validated (V2 — 87% win rate, blind A/B)
- [x] Skill caching validated (V3 — +69.2% lift, 0 regressions)
- [ ] Cross-model portability test (Claude + Gemini + GPT-4o)
- [ ] V3 scale-up to 50–100 trials
- [ ] arXiv paper submission
- [ ] pip install convoseed

---

## Licence

Apache 2.0. Open forever.

---

## Contact

Open an Issue for technical questions.  
For collaboration or research enquiries: see CONTRIBUTING.md.

*"AI memory is a format problem, not a storage problem."*