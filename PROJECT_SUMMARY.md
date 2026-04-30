# ConvoSeed — Project Summary
> Generated: 2026-04-30

---

## What We've Done

- **Defined CSP-1 Protocol (v0.2 → v1.1 → v2.0)** — A portable `.fp` fingerprint format (~200KB) for encoding AI conversational identity, user-owned and model-agnostic
- **Built the core encoder pipeline** — Conversation → LLM summary → SBERT embeddings → PCA compression (k=4) → HDC binding (10,000-dim) → ZIP `.fp` archive
- **Built speaker identification** — Cosine-similarity matching against HDC seeds; 52% accuracy on 10 candidates vs 10% baseline (p < 10⁻¹⁰⁰, 5.2× over chance)
- **Built style-conditioned generation (decode)** — Prefix-tuned generation conditioned on extracted `.fp` summary
- **Published `convoseed-agent` to PyPI** — Installable package with CLI entry points (`convoseed-encode`, `convoseed-identify`)
- **Added GitHub Actions CI/CD** — Auto-publishes to PyPI on git tag push
- **Validated V1: Speaker ID** — 52% accuracy over 1,000 trials on a 524-message real conversation dataset
- **Validated V2: Cross-model style preservation** — 97.8% win rate (44/45) across Claude Sonnet 4.6, GPT-4o, Gemini 1.5 Flash; +449% average style lift without retuning
- **Validated V3: Skill caching** — 88/100 WITH vs 54/100 WITHOUT fingerprint (+63% relative lift, 100 trials, 5 task types, Claude-only)
- **Ran Gemma3:12b experiments** — Style generation similarity 0.523 avg; stored results in `experiments/gemma3_12b_results.json`
- **Killed a false claim** — Removed invalid 12.7% lift stat; replaced with honest V1/V2/V3 results
- **Wrote the research paper** — Full LaTeX source + 4 figures (architecture, win rates, skill cache, stack) in `paper/`
- **Prepared arXiv submission** — Abstract with honest methodology and limitations in `docs/abstract.md`
- **Wrote protocol spec** — `spec/CSP-1.md` formally defines v2.0 `.fp` file format
- **Cleaned up codebase** — Deleted unused modules (scheduler, registry, encoder cache, wrapper), bumped to v2.0.0

---

## What's Next

| # | Area | Gap | How to Resolve |
|---|------|-----|----------------|
| 1 | **V3 Cross-Model Skill Validation** | Skill caching (V3) only validated on Claude; GPT-4o and Gemini results missing | Run `tests/v3_skill_cache/csp1_task_test_v2.jsx` against GPT-4o and Gemini APIs; publish results alongside Claude baseline |
| 2 | **Fingerprint Signing (`sign.py`)** | `TODO` in `encode.py:143` — no cryptographic signature mechanism for fingerprint authenticity | Implement `sign.py` using `cryptography` lib (already in deps); add Ed25519 key pair generation + detached signature field in `manifest.json` |
| 3 | **HDC-to-Text Decoding** | Hyperdimensional vectors currently undecodable back to natural language | Research HD computing inverse mappings; explore learned approximate inverse via small decoder MLP trained on (HDC vector, original text) pairs |
| 4 | **CHUNKS Scaling (>500 messages)** | Protocol has no composition rules for long conversations; single `.fp` becomes lossy | Define `CHUNKS` field in CSP-1 spec; implement sliding-window encoder with per-chunk `.fp` + merge strategy (e.g., weighted PCA average) |
| 5 | **Multi-Lingual Support** | SBERT supports 50+ languages but completely untested; claimed portability may not hold | Run V1/V2 experiments with non-English conversations using `paraphrase-multilingual-MiniLM-L12-v2`; document per-language accuracy |
| 6 | **Real Conversation Dataset for Publication** | Only `sample_conversation.json` (20 msgs) is public; paper reviewers will ask for larger eval set | Recruit 10-20 participants to donate anonymized conversations; build anonymization pipeline; publish as HuggingFace dataset |
| 7 | **`examples/` Directory** | `examples/README.md` is a placeholder — no sample `.fp` files for new users to inspect | Generate 3-5 anonymized `.fp` files from public conversations (e.g., open GitHub issues threads); add to `examples/` with descriptions |
| 8 | **Platform Adoption / Incentive Design** | No reason for AI platforms (OpenAI, Google) to support a format that reduces lock-in | Write an interoperability proposal; frame as user-trust / portability feature; open a GitHub Discussions thread for community input |
| 9 | **Dependency: `cryptography` unused** | Listed as optional dep but no code uses it yet (pending `sign.py`) | Either implement signing (item #2) or remove from `pyproject.toml` to reduce install footprint |
| 10 | **arXiv Submission** | Paper is ready locally but not yet submitted | Run final LaTeX build check → upload to arXiv cs.AI → get identifier → add to README badge and PyPI description |
| 11 | **`docs/README.md` empty** | Placeholder file with no content | Either populate with rendered docs (e.g., Sphinx/MkDocs) or delete and redirect to main README to avoid confusion |
| 12 | **Test Coverage** | No pytest unit tests exist despite `pytest` being a dev dep | Write unit tests for `encode.py` (round-trip), `identify.py` (mock SBERT), `decode.py` (output format); aim for >80% coverage |
