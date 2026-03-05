# ConvoSeed: The Cognitive Fingerprint Protocol (CSP-1)

> *"AI memory is a format problem, not a storage problem."*

I had a friend — an AI that finally "got" me. It understood my shorthand, my messy logic, and the weird detours I take before I ever get to the point. Then the session ended. One refresh, and I was talking to a stranger again.

ConvoSeed is the answer to digital amnesia. A 200KB `.fp` file that captures how you communicate. Load it into Claude, GPT-4o, or Gemini — it doesn't matter. The conversation doesn't start over. It resumes.

---

## Results (March 2026)

### V2 — Style Preservation · Cross-Model Validated

Method: Blind A/B, 15 trials per model, 5 personas, Claude-as-judge, randomized presentation.
Fingerprints generated once on Claude and transferred cold to GPT-4o and Gemini. No retuning.

| Model | Win Rate | Avg WITH | Avg WITHOUT | Lift |
|-------|----------|----------|-------------|------|
| Claude Sonnet 4.6 | 100% (15/15) | 9.13/10 | 1.67/10 | +448% |
| GPT-4o | 93% (14/15) | ~5.5/10 | ~1.1/10 | ~+400% |
| Gemini 1.5 Flash | 100% (15/15) | 6.4/10 | 1.07/10 | +500% |
| **Combined** | **97.8% (44/45)** | **~7.0/10** | **~1.28/10** | **+449%** |

### V1 — Speaker Identification

- SBERT→PCA→HDC encoder on a real 524-message conversation
- **p < 10⁻¹⁰⁰** across 1,000 trials
- Distinguishes unique conversational styles with statistical certainty

### V3 — Skill Caching

- Hard tasks calibrated for ~50% baseline failure rate
- **88/100 WITH vs 54/100 WITHOUT (+63.0% relative lift)**
- FP decisive: 34/100 · FP harmful: 0/100
- Consistent 88% WITH across all 4 independent runs — not noise

---

## How It Works

```
Conversation → LLM Summary → summary.txt → .fp ZIP archive
                                                  ↓
                              system_prompt = summary.txt + original_prompt
```

Three things happen inside CSP-1:

1. **Distillation** — A conversation is compressed into a 60–100 word LLM-generated summary capturing style, vocabulary, reasoning patterns, and task knowledge
2. **Encoding** — The summary is packed into a `.fp` ZIP archive alongside optional HDC retrieval vectors
3. **Injection** — At runtime, `summary.txt` is prepended to the system prompt on any model

The performance gains come from the text summary. The SBERT→PCA→HDC encoder handles speaker identification and retrieval separately — it is not the source of the stylistic improvement.

---

## The `.fp` File Format

A fixed-size (~200KB) ZIP archive:

| File | Description |
|------|-------------|
| `manifest.json` | Protocol version, fp_type, task_type, success_score |
| `summary.txt` | LLM-generated style/skill description (60–100 words) |
| `metadata.json` | Timestamp, model origin, token counts |
| `vector.bin` | Optional HDC-encoded retrieval vector |

Fixed size regardless of conversation length. User-owned. Model-agnostic.

---

## Quick Start

```bash
pip install anthropic sentence-transformers scikit-learn numpy

# Generate a fingerprint from a conversation
python tools/fp_create.py --input conversation.json --output identity.fp --type identity

# Run the cross-model style validation
python tests/cross_model/convoseed_ab_test.py --models claude gpt4 gemini
```

---

## Where CSP-1 Fits

The emerging agent identity stack has two established layers. CSP-1 is the third:

| Layer | Covers | Status |
|-------|--------|--------|
| DID (W3C) | Who the user IS cryptographically | Specified |
| MCP (Anthropic) | What tools the agent can ACCESS | Specified |
| **CSP-1** | **How the user SPEAKS and THINKS** | **This work** |

DID answers *who*. MCP answers *what*. CSP-1 answers *how*.

---

## Honest Claims

```
V1: "SBERT→PCA→HDC distinguishes conversational styles at p < 10⁻¹⁰⁰
     across 1,000 trials on a real 524-message conversation."

V2: "CSP-1 text-summary fingerprints achieve 97.8% win rate across three
     frontier model families (44/45 trials). Fingerprints transferred
     cold from Claude to GPT-4o and Gemini without modification."

V3: "Skill fingerprints improved task success from 54% to 88% (+63.0%
     relative lift) across 100 trials, 5 task types, binary scoring.
     FP decisive: 34/100. FP harmful: 0/100."
```

**Future work:** Cross-model V3 (skill portability), HDC-to-text decoding, conversations >500 messages.

**Killed claims:** "12.7% lift" (was model size comparison, not FP vs no-FP). Not resurrected.

---

## Open Challenges

Collaboration welcome — open an Issue.

1. **Cross-Model Skill Portability** — V3 fingerprints validated on Claude only. Does skill caching transfer to GPT-4o and Gemini?
2. **HDC Decode** — The encoder is validated for identification. Generating text from hyperdimensional vectors remains unsolved.
3. **CHUNKS Scaling** — Composition rules for conversations exceeding 500 messages while preserving the fixed 200KB constraint.

---

## Repository Structure

```
ConvoSeed/
├── tools/
│   └── fp_create.py               ← CLI to generate .fp files
├── tests/
│   ├── cross_model/
│   │   └── convoseed_ab_test.py   ← Claude + GPT-4o + Gemini validation
│   ├── v2_style_ab/
│   │   └── convoseed_ab_test.jsx  ← Browser A/B test harness
│   └── v3_skill_cache/
│       └── csp1_task_test_v2.jsx  ← Hard task skill caching (n=100)
├── docs/
│   └── abstract.md                ← arXiv abstract draft
└── src/                           ← Encoder / decoder / identifier
```

---

## Licence

Apache 2.0. Open forever.

## Contact

Open an Issue for technical questions.
For collaboration or research enquiries: see CONTRIBUTING.md.

*"AI memory is a format problem, not a storage problem."*
