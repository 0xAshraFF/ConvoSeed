# CSP-1: A Portable Protocol for Conversational Identity and Skill Caching in Large Language Models

**Authors:** Ashraful Islam (0xAshraFF)  
**Date:** March 2026  
**Repository:** https://github.com/0xAshraFF/ConvoSeed  
**License:** Apache 2.0

---

## Abstract

Every interaction with a large language model begins from zero. Users rebuild
context, vocabulary, and working rapport across sessions — an invisible tax on
human-AI collaboration. We present CSP-1 (Conversational State Protocol 1), an
open protocol that encodes human-AI conversational identity and agent skill
knowledge into portable, user-owned `.fp` files of approximately 200KB.

A `.fp` file is a ZIP archive containing a mandatory LLM-generated text summary
(`summary.txt`) and optional Hyperdimensional Computing (HDC) vectors for
similarity retrieval. Conditioning is achieved by prepending the summary to the
system prompt: `system = summary.txt + "\n\n" + original_prompt`. The protocol
is model-agnostic, requires no fine-tuning, and imposes no vendor dependency.

We report three empirical validations:

**V1 — Speaker Identification.** A SBERT→PCA→HDC encoder distinguishes
conversational styles at p < 10⁻¹⁰⁰ across 1,000 trials on a real 524-message
human-AI conversation, demonstrating that HDC-encoded fingerprints carry
statistically significant identity signal.

**V2 — Identity Preservation.** In a randomized blind A/B evaluation, CSP-1
text-summary fingerprints achieved an 87% win rate in stylistic consistency
(15 trials, 5 personas, 9.0/10 vs 2.67/10, Claude-as-judge). The large effect
size (Δ = 6.33/10) suggests robust style transfer across diverse writing registers.

**V3 — Skill Caching.** On a suite of ambiguous edge-case tasks calibrated for
approximately 50% baseline failure, skill fingerprints improved task success from
54% to 88% (+63.0% relative lift) across 100 ground-truth trials, 5 task types,
binary pass/fail automated scoring. Fingerprints were decisive in 34/100 trials
and harmful in 0/100 trials, indicating a reliable one-directional improvement.

The HDC layer is validated for retrieval; the performance gains arise from
LLM-generated text summaries injected as system prompts — a finding we report
explicitly to avoid overstating the role of the binary encoding. Cross-model
portability (Claude, Gemini, GPT-4o) is the primary remaining open question.

CSP-1 is positioned as the third layer of the emerging agent identity stack,
complementing W3C DIDs (cryptographic identity) and Anthropic MCP (tool access)
with a portable representation of how a user thinks and communicates.
The protocol is released under Apache 2.0 to encourage adoption as an open standard.

---

## Keywords

conversational AI, memory, identity, portability, hyperdimensional computing,
skill caching, system prompt conditioning, open protocol, user-owned AI

---

## Honest Limitations

- V2 uses Claude-as-judge; LLM evaluation bias is acknowledged (see Zheng et al., 2023)
- V3 uses a single model (Claude Sonnet); cross-model generalization is pending
- No human evaluation component; informal human validation is recommended
- HDC decode (text reconstruction from vectors) remains an unsolved research problem

---

## Honest Claims (copy-paste ready)

```
V1: "The SBERT→PCA→HDC encoder distinguishes conversational styles at
p < 10⁻¹⁰⁰ across 1,000 trials on a real 524-message conversation."

V2: "CSP-1 text-summary fingerprints achieved an 87% win rate in stylistic
consistency (15 trials, 5 personas, 9.0/10 vs 2.67/10, Claude-as-judge,
randomized blind presentation)."

V3: "On ambiguous edge-case tasks calibrated for ~50% baseline failure, skill
fingerprints improved task success from 54% to 88% (+63.0% relative lift)
across 100 ground-truth trials, 5 task types, binary pass/fail scoring.
FP decisive: 34/100. FP harmful: 0/100."
```

---

## Recommended Paper Structure

1. Abstract
2. Introduction — the reset problem; the emotional insight; technical framing
3. Related Work — MemGPT, RAG, context distillation, user modeling, prefix tuning
4. CSP-1 Protocol — .fp format, injection method, HDC retrieval, registry
5. Experiments — V1 (speaker ID), V2 (style A/B), V3 (skill caching)
6. Discussion — what summary.txt vs HDC each contribute; portability as future work
7. Limitations — LLM-as-judge, single model, sample sizes
8. Conclusion

---

*"AI memory is a format problem, not a storage problem."*
