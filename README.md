# ConvoSeed

CSP-1 is the **missing third leg** of the agent identity stack:

| Layer | Covers | Status |
|---|---|---|
| DID (W3C) | Who the user IS cryptographically | Specified |
| MCP (Anthropic) | What tools the agent can ACCESS | Specified |
| **CSP-1** | **How the user SPEAKS and THINKS** | **This work** |

**Chat → Compress → 200KB `.fp` File → Decompress → Resume**

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

## Results (February 2026)

Validated on a real **524-message** researcher-AI conversation.

| Model | Avg Similarity | Peak | Msgs > 0.7 |
|---|---|---|---|
| GPT-2 (124M) | 0.464 | 1.000 | 1 |
| Gemma3:1b | 0.466 | 0.707 | 1 |
| **Gemma3:12b** | **0.523** | **0.757** | **4** |

- **+12.7%** improvement from 1B → 12B parameters
- **232×** more efficient than VAE baseline
- **p < 10⁻¹⁰⁰** statistical significance on speaker identification task

---

## How It Works

```
Messages → SBERT embed → PCA compress → HDC bind → Prefix tune → .fp file
```

1. **Embed** — Sentence-BERT encodes each message into a 384-dim vector
2. **Compress** — PCA extracts the style centroid (4 components = full accuracy)
3. **Bind** — Hyperdimensional Computing (10,000-dim) weaves temporal sequence into one vector
4. **Tune** — A prefix tensor conditions the LLM to regenerate in your style
5. **Sign** — Ed25519 cryptographic signature proves ownership

---

## File Format (`.fp`)

| Section | Size | Description |
|---|---|---|
| HEADER | ~1 KB | Magic bytes + version + CRC-32 |
| PCA_MODEL | ~8 KB | Style centroid: mean + eigenvectors |
| HDC_SEED | ~140 KB | 10,000-dim hypervector (float16) |
| PREFIX | ~40 KB | Prefix tuning tensor for generation |
| SIGNATURE | ~1 KB | Ed25519 ownership proof |
| CHUNKS | ~10 KB | Index for 500+ message threads |

**Total: ~200KB — fixed size regardless of conversation length.**

See [`/spec/CSP-1.md`](spec/CSP-1.md) for the full binary specification.

---

## Quick Start

```bash
pip install sentence-transformers scikit-learn numpy

# Encode a conversation
python src/encode.py --input my_conversation.json --output identity.fp

# Identify a speaker
python src/identify.py --query "new message here" --candidates *.fp

# Generate in someone's style
python src/decode.py --fp identity.fp --prompt "Tell me about your day"
```

---

## Repository Structure

```
ConvoSeed/
├── README.md
├── LICENSE                          ← MIT
├── CONTRIBUTING.md
├── /docs
│   ├── ConvoSeed_Whitepaper.docx    ← arXiv-ready academic paper
│   ├── ConvoSeed_ResearchPaper.docx ← detailed technical paper
│   ├── ConvoSeed_Poster.pdf      ← conference poster (CHI 2026)
│   └── ConvoSeed_ProtocolSpec.pdf ← protocol specification sheet
├── /spec
│   └── CSP-1.md                     ← plain-text binary spec
├── /src
│   ├── encode.py                    ← fingerprint encoder
│   ├── decode.py                    ← style-conditioned generation
│   └── identify.py                  ← speaker identification
├── /experiments
│   └── gemma3_12b_results.json      ← February 2026 experimental results
└── /examples
    └── sample_identity.fp           ← anonymised example fingerprint
```

---

## Documents

| Document | Format | Description |
|---|---|---|
| [Whitepaper](docs/ConvoSeed_Whitepaper.docx) | DOCX | 6-section academic paper, arXiv-ready |
| [Research Paper](docs/ConvoSeed_ResearchPaper.docx) | DOCX | Full technical paper with equations + references |
| [Conference Poster](docs/ConvoSeed_Poster.pdf) | PDF | CHI 2026 style research poster |
| [Protocol Spec Sheet](docs/ConvoSeed_ProtocolSpec.pdf) | PDF | One-page technical specification |
| [Presentation](docs/ConvoSeed_Presentation.pptx) | PPTX | 12-slide pitch deck |
| [W3C Note](docs/ConvoSeed_W3C_Note.pdf) | PDF | Submission to W3C AI Agent Protocol CG |

---

## Open Challenges

These are the three open research questions. Collaboration welcome — open an Issue.

1. **Cross-Model Mapping** — translating a `.fp` fingerprint trained on SBERT embeddings into GPT-4 or other backbone spaces without re-encoding the original conversation.

2. **CHUNKS Scaling** — formal composition rules for the CHUNKS section when threads exceed 500 messages, while preserving the fixed 200KB file size.

3. **Incentive Design** — what makes AI platforms adopt an open standard that reduces their own lock-in?

---

## Status

> Early research. Proof-of-concept validated on real data. Open for collaboration.

- [x] Protocol specification (CSP-1 v0.2)
- [x] Proof-of-concept encoder/decoder
- [x] Speaker identification experiment (1,000 trials)
- [x] Multi-model validation (GPT-2, Gemma3:1b, Gemma3:12b)
- [x] Real conversation validation (524 messages)
- [ ] Multi-speaker support
- [ ] Cross-model mapping
- [ ] Public dataset (seeking contributors)
- [ ] W3C Community Group submission

---

## Licence

MIT. Open forever.

---

## Contact

Open an Issue for technical questions.  
For collaboration or research enquiries: see CONTRIBUTING.md.
