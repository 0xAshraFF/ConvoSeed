# Contributing to ConvoSeed

Thank you for your interest in contributing. ConvoSeed is an early-stage,
open research. Every contribution — code, feedback, data, or ideas — matters.

---

## Where Help Is Most Needed

### 1. Cross-Model Mapping (Research)
The `.fp` fingerprint is currently SBERT-specific. We need a method to
translate a fingerprint trained on SBERT embeddings into GPT-4, Claude,
or other embedding spaces without re-encoding the original conversation.

**Useful background:** linear probing, CKA (Centered Kernel Alignment),
embedding space alignment, anchor-based translation.

### 2. CHUNKS Composition (Engineering + Research)
The CHUNKS section allows long conversations (500+ messages) to be indexed
in chunks. The composition rule (majority-bind of chunk seeds) needs:
- Formal proof of style preservation under composition
- Empirical validation that global seed quality degrades gracefully
- Design of an incremental update mechanism (new messages don't require full re-encode)

### 3. Real Conversation Dataset
The current validation uses one conversation. To publish this work,
we need a dataset of diverse conversations (different speakers, topics,
languages). If you have AI chat logs and are willing to share anonymised
versions, please open an Issue.

### 4. Multi-Lingual Support
SBERT supports 50+ languages. Test CSP-1 on non-English conversations
and report results.

### 5. Incentive Design (Not Engineering)
This is a social science/economics question: what makes AI platforms
choose to support an open standard that reduces their own lock-in?
Papers, frameworks and historical analogies welcome.

---

## How to Contribute

1. **Open an Issue** before starting work — describe what you want to do.
2. **Fork** the repository and create a branch: `git checkout -b feature/your-feature`
3. **Write clear commit messages** — what changed and why.
4. **Open a Pull Request** — link the relevant Issue.

---

## Code Standards

- Python 3.10+
- Type hints where possible
- Docstrings on all public functions
- No dependencies beyond: `sentence-transformers`, `scikit-learn`, `numpy`, `cryptography`

---

## Data Privacy

If contributing conversation data:
- Anonymise all identifying information
- Remove names, locations and account details
- Ensure you have the right to share the content
- Preference for data where both parties consented to research use

---

## Questions

Open an Issue with the label `question`. No question is too basic.

---

*"You don't need the whole orchestra. Just the lead violin."*
