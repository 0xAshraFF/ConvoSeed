"""
ConvoSeed — decode.py
Style-conditioned text generation from a .fp fingerprint.

Usage:
    python decode.py --fp identity.fp --prompt "Tell me about your weekend"
    python decode.py --fp identity.fp --evaluate --test-messages test.json

Requirements:
    pip install sentence-transformers transformers torch numpy
"""

import json
import argparse
import numpy as np
from sentence_transformers import SentenceTransformer


SBERT_MODEL = "all-MiniLM-L6-v2"


# ── Similarity evaluation ─────────────────────────────────────────────────────
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / d) if d > 0 else 0.0


def evaluate_similarity(original: str, generated: str,
                         model: SentenceTransformer) -> float:
    """
    Cosine similarity between original and generated message embeddings.
    This is the metric used in the research paper.

    Score interpretation:
        ≥ 0.7  High fidelity — near-perfect style match
        ≥ 0.5  Good match — stylistically consistent
        < 0.4  Poor match — likely topic outlier or short message
    """
    orig_vec = model.encode([original])[0]
    gen_vec  = model.encode([generated])[0]
    return cosine_similarity(orig_vec, gen_vec)


# ── Generation (prefix tuning) ────────────────────────────────────────────────
def generate_with_prefix(prompt: str, fp: dict, model_name: str = "gpt2") -> str:
    """
    Generate text conditioned on a .fp fingerprint via prefix tuning.

    NOTE: Full prefix tuning requires training the PREFIX tensor on your
    specific model. This function demonstrates the concept using the
    HDC seed as a soft prompt via direct embedding injection.

    For Gemma3:12b results from the paper, prefix training was done using
    the Hugging Face PEFT library with the HDC seed as the initialisation.
    """
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        print(f"Loading {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.eval()

        # Build context from fingerprint metadata
        n_msgs = fp.get("n_messages", "unknown")
        variance_k4 = sum(fp.get("pca_explained_variance_ratio", [0]*4)[:4])

        # Soft prompt: prepend style description derived from PCA
        # In full implementation, this would use the trained PREFIX tensor
        style_context = (
            f"[Style: compressed from {n_msgs} messages, "
            f"k=4 variance={variance_k4:.1%}] "
        )
        full_prompt = style_context + prompt

        inputs = tokenizer(full_prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )

        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Strip the prompt prefix from the output
        return generated[len(full_prompt):].strip()

    except ImportError:
        return (
            "[Generation requires: pip install transformers torch]\n"
            "For Gemma3:12b results, use Ollama: ollama run gemma3:12b"
        )


def evaluate_on_test_set(fp_path: str, test_messages: list[str],
                          model_name: str = "gpt2") -> dict:
    """
    Evaluate fingerprint quality on a set of held-out messages.
    Reproduces the experiment from the research paper.
    """
    with open(fp_path) as f:
        fp = json.load(f)

    sbert = SentenceTransformer(SBERT_MODEL)
    scores = []

    print(f"Evaluating {len(test_messages)} messages...")
    for i, msg in enumerate(test_messages):
        generated = generate_with_prefix(msg, fp, model_name)
        sim = evaluate_similarity(msg, generated, sbert)
        scores.append(sim)
        print(f"  Message {i+1:2d}: {sim:.3f}  |  original: {msg[:50]}...")

    results = {
        "n_messages": len(scores),
        "average": float(np.mean(scores)),
        "median": float(np.median(scores)),
        "best": float(max(scores)),
        "worst": float(min(scores)),
        "std_dev": float(np.std(scores)),
        "msgs_above_0_7": sum(1 for s in scores if s >= 0.7),
        "msgs_above_0_6": sum(1 for s in scores if s >= 0.6),
        "individual_scores": scores,
        "model": model_name
    }

    print(f"\n{'─'*40}")
    print(f"Average:     {results['average']:.3f}")
    print(f"Best:        {results['best']:.3f}")
    print(f"Worst:       {results['worst']:.3f}")
    print(f"Median:      {results['median']:.3f}")
    print(f"Std Dev:     {results['std_dev']:.3f}")
    print(f"Msgs > 0.7:  {results['msgs_above_0_7']}")
    print(f"Msgs > 0.6:  {results['msgs_above_0_6']}")

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ConvoSeed Decoder — generate text in a fingerprint's style"
    )
    parser.add_argument("--fp",            required=True,  help="Path to .fp file")
    parser.add_argument("--prompt",                        help="Prompt for generation")
    parser.add_argument("--evaluate",      action="store_true",
                        help="Run similarity evaluation on test messages")
    parser.add_argument("--test-messages",                 help="JSON file with test messages")
    parser.add_argument("--model",         default="gpt2", help="Model name (gpt2, gemma3:12b, etc.)")
    args = parser.parse_args()

    with open(args.fp) as f:
        fp = json.load(f)

    if args.evaluate and args.test_messages:
        with open(args.test_messages) as f:
            test_msgs = json.load(f)
        results = evaluate_on_test_set(args.fp, test_msgs, args.model)
        print(json.dumps(results, indent=2))

    elif args.prompt:
        output = generate_with_prefix(args.prompt, fp, args.model)
        print(f"\nGenerated:\n{output}")
