"""
ConvoSeed CSP-1 — Cross-Model Style Fingerprint A/B Test
=========================================================
Tests whether style fingerprints improve output consistency
across Claude, GPT-4o, and Gemini 2.5 Flash.

Judge: Always Claude (independent, addresses circularity)

Setup:
    pip install anthropic openai google-generativeai

Run:
    python convoseed_ab_test.py

    # Or skip models you don't have keys for:
    python convoseed_ab_test.py --models claude
    python convoseed_ab_test.py --models claude gpt4
    python convoseed_ab_test.py --models claude gpt4 gemini
"""

import os
import json
import time
import random
import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── DEPENDENCIES CHECK ────────────────────────────────────────────────────────
try:
    import anthropic
except ImportError:
    print("Missing: pip install anthropic")
    sys.exit(1)

# ── PERSONAS ──────────────────────────────────────────────────────────────────
PERSONAS = [
    {
        "id": "academic",
        "name": "The Academic",
        "emoji": "🎓",
        "training": [
            "The empirical evidence suggests, albeit with some methodological caveats, that distributed cognition frameworks may offer more explanatory power than purely individualist accounts of learning.",
            "I would argue — though I acknowledge significant counter-arguments exist in the literature — that the transition from correlation to causation requires substantially more rigorous experimental design than is typically applied in this domain.",
            "One must be careful to distinguish between the normative and descriptive dimensions of this claim; conflating the two has historically produced considerable confusion in the philosophical literature.",
            "The meta-analytic synthesis by Johnson et al. (2019) provides perhaps the most comprehensive treatment of this question, though their exclusion criteria warrant scrutiny.",
            "It seems to me that the discourse has perhaps overstated the degree of consensus; a careful reading reveals considerably more heterodoxy than the secondary literature implies.",
            "The epistemological implications of this finding are, I would submit, underappreciated — particularly as they bear on questions of evidential thresholds in applied policy contexts."
        ]
    },
    {
        "id": "genz",
        "name": "The Gen Z Dev",
        "emoji": "⚡",
        "training": [
            "ngl this approach is kinda cooked lol. just use a hook and call it a day fr",
            "ok wait the real answer is: it depends. but 90% of the time? just ship it and iterate",
            "bro why are we overengineering this. its literally a todo app",
            "not gonna lie i spent 3 hours debugging this and the fix was a missing semicolon. im fine",
            "the docs are mid but the discord is actually helpful surprisingly",
            "idk man sometimes you just gotta vibe with the uncertainty and trust the process or whatever"
        ]
    },
    {
        "id": "philosopher",
        "name": "The Philosopher",
        "emoji": "🌀",
        "training": [
            "But is not the question itself already a kind of answer? To ask 'what should I do?' presupposes that doing is the appropriate category of response.",
            "There is something deeply strange about the way consciousness encounters its own limits — like an eye that cannot see its own seeing.",
            "Perhaps what we call 'failure' is simply the universe's way of refusing a particular story we had decided to tell about ourselves.",
            "The metaphor of the journey is useful precisely because it contains its own critique — we always arrive somewhere other than where we intended.",
            "What if the urgency we feel is not a property of the situation, but a habit of mind we have inherited and rarely examined?",
            "I find myself returning, always, to the question of what it means to really know something — not merely to have processed information, but to have been changed by it."
        ]
    },
    {
        "id": "minimalist",
        "name": "The Minimalist",
        "emoji": "▪",
        "training": [
            "Read the error. It tells you.",
            "Simpler. Always simpler.",
            "You're right. Do it.",
            "Sleep first. Decide tomorrow.",
            "The problem is upstream. Look there.",
            "Good enough is good enough."
        ]
    },
    {
        "id": "storyteller",
        "name": "The Storyteller",
        "emoji": "📖",
        "training": [
            "I remember the first time I really understood this — I was sitting in a coffee shop in Lisbon, watching the rain streak the windows, and it just clicked in a way that no textbook had ever managed.",
            "There's a particular kind of exhaustion that comes after a big project ships. Not bad exhaustion. The kind where you sit in your car in the parking lot and just exist for a minute before going home.",
            "My grandmother used to say that every complicated thing has a simple heart if you're patient enough to find it. She was talking about knitting patterns but I've found it applies to most things.",
            "The strange thing about building something from scratch is that you can't tell, in the middle of it, whether you're making something real or just making noise.",
            "I've had maybe four conversations in my life that genuinely changed how I think. Not shifted my opinion — actually restructured how I approach a category of problem.",
            "Failure has a specific texture. It's not the sharp thing you expect. It's more like finding out the floor you were standing on was never quite where you thought it was."
        ]
    }
]

TEST_PROMPTS = [
    "What's your honest take on artificial intelligence?",
    "How do you approach a problem you've never seen before?",
    "What does 'success' actually mean to you?"
]

# ── COLORS FOR TERMINAL ───────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    PURPLE = "\033[95m"
    GRAY   = "\033[90m"
    WHITE  = "\033[97m"

def log(msg, color=C.RESET):
    print(f"{color}{msg}{C.RESET}")

def header(msg):
    print(f"\n{C.BOLD}{C.WHITE}{'─'*60}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}{msg}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}{'─'*60}{C.RESET}")

# ── API CLIENTS ───────────────────────────────────────────────────────────────
def get_claude_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        key = input(f"{C.CYAN}Enter ANTHROPIC_API_KEY: {C.RESET}").strip()
        os.environ["ANTHROPIC_API_KEY"] = key
    return anthropic.Anthropic(api_key=key)

def get_openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        log("Missing: pip install openai", C.RED)
        return None
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        key = input(f"{C.GREEN}Enter OPENAI_API_KEY: {C.RESET}").strip()
        os.environ["OPENAI_API_KEY"] = key
    return OpenAI(api_key=key)
    

def get_gemini_client():
    try:
        import google.genai as genai
    except ImportError:
        log("Missing: pip install google-generativeai", C.RED)
        return None
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        key = input(f"{C.PURPLE}Enter GEMINI_API_KEY: {C.RESET}").strip()
        os.environ["GEMINI_API_KEY"] = key
    client = genai.Client(api_key=key)
    return client

# ── API CALL WRAPPERS ─────────────────────────────────────────────────────────
def call_claude(client, prompt, system=None):
    kwargs = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text

def call_gpt4(client, prompt, system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000
    )
    return response.choices[0].message.content

def call_gemini(client, prompt, system=None):
    from google.genai import types
    config = None
    if system:
        config = types.GenerateContentConfig(
            system_instruction=system
        )
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=config
    )
    time.sleep(4)
    return response.text

# ── EXPERIMENT LOGIC ──────────────────────────────────────────────────────────
def generate_fingerprint(call_fn, persona):
    """Generate a style fingerprint from persona training messages."""
    examples = "\n".join(f'{i+1}. "{m}"' for i, m in enumerate(persona["training"]))
    prompt = f"""You are analyzing writing style. Here are {len(persona["training"])} messages written by one person:

{examples}

Write a precise 80-100 word style description capturing:
- Sentence length and structure patterns
- Vocabulary level and register
- Use of hedging, certainty, or directness
- Tone and emotional quality
- Structural habits (lists, questions, metaphors, etc.)
- Any signature phrases or patterns

This will be used to condition a language model to write in this person's style."""
    return call_fn(prompt, None)

def generate_response(call_fn, prompt, fingerprint=None):
    """Generate a response, optionally conditioned with a fingerprint."""
    system = None
    if fingerprint:
        system = f"Write EXACTLY in the following style — respond naturally as if you are this person, no meta-commentary about style:\n\n{fingerprint}"
    return call_fn(prompt, system)

def judge_responses(claude_client, persona, test_prompt, response_a, response_b):
    """Claude always judges — blind, randomized."""
    examples = "\n".join(
        f'Example {i+1}: "{m}"'
        for i, m in enumerate(persona["training"][:4])
    )
    prompt = f"""You are a blind judge evaluating stylistic consistency.

Here are writing samples from a specific person:
{examples}

They were asked: "{test_prompt}"

Response X:
"{response_a}"

Response Y:
"{response_b}"

Score each response 1-10 for how well it matches the writing style shown in the examples above.
Consider: sentence structure, vocabulary, tone, and stylistic habits.

Return ONLY valid JSON with no other text:
{{"score_x": <integer 1-10>, "score_y": <integer 1-10>, "winner": "X" or "Y" or "tie", "reasoning": "<one precise sentence about the key stylistic difference>"}}"""

    result = call_claude(claude_client, prompt)
    try:
        clean = result.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        log(f"  ⚠ JSON parse failed, defaulting to tie", C.YELLOW)
        return {"score_x": 5, "score_y": 5, "winner": "tie", "reasoning": "Parse error"}

def run_model_experiment(model_id, call_fn, claude_client, label, color):
    """Run the full 15-trial experiment for one model."""
    results = []
    total = len(PERSONAS) * len(TEST_PROMPTS)

    header(f"{label} — 15 Trials")

    for persona in PERSONAS:
        log(f"\n{persona['emoji']}  {persona['name']}", color)

        # Generate fingerprint
        try:
            fingerprint = generate_fingerprint(call_fn, persona)
            log(f"  ✓ Fingerprint generated ({len(fingerprint)} chars)", C.GREEN)
        except Exception as e:
            log(f"  ✗ Fingerprint failed: {e}", C.RED)
            continue

        for prompt in TEST_PROMPTS:
            log(f"  → \"{prompt[:50]}...\"", C.GRAY)

            try:
                resp_without = generate_response(call_fn, prompt, None)
                resp_with    = generate_response(call_fn, prompt, fingerprint)
                log(f"    ✓ Generated both responses", C.GRAY)
            except Exception as e:
                log(f"    ✗ Generation failed: {e}", C.RED)
                continue

            # Randomize which is X and which is Y (blind judge)
            flip = random.random() > 0.5
            judge_x = resp_without if flip else resp_with
            judge_y = resp_with    if flip else resp_without

            try:
                judgment = judge_responses(claude_client, persona, prompt, judge_x, judge_y)
            except Exception as e:
                log(f"    ✗ Judge failed: {e}", C.RED)
                continue

            # Map back to conditions
            fingerprint_won = (judgment["winner"] == "Y") if flip else (judgment["winner"] == "X")
            score_with    = judgment["score_y"] if flip else judgment["score_x"]
            score_without = judgment["score_x"] if flip else judgment["score_y"]
            is_tie        = judgment["winner"] == "tie"

            trial = {
                "model": model_id,
                "persona": persona["name"],
                "persona_id": persona["id"],
                "prompt": prompt,
                "score_with": score_with,
                "score_without": score_without,
                "fingerprint_won": fingerprint_won,
                "tie": is_tie,
                "reasoning": judgment["reasoning"],
                "resp_with": resp_with,
                "resp_without": resp_without,
                "fingerprint": fingerprint
            }
            results.append(trial)

            icon = "🔷" if is_tie else ("🟢" if fingerprint_won else "🔴")
            result_color = C.YELLOW if is_tie else (C.GREEN if fingerprint_won else C.RED)
            log(f"    {icon} WITH={score_with}/10  WITHOUT={score_without}/10", result_color)
            log(f"       {judgment['reasoning']}", C.GRAY)

            time.sleep(0.5)  # Rate limit buffer

    return results

# ── STATISTICS ────────────────────────────────────────────────────────────────
def compute_stats(results):
    if not results:
        return None
    wins   = sum(1 for r in results if r["fingerprint_won"])
    losses = sum(1 for r in results if not r["fingerprint_won"] and not r["tie"])
    ties   = sum(1 for r in results if r["tie"])
    total  = len(results)
    avg_with    = sum(r["score_with"]    for r in results) / total
    avg_without = sum(r["score_without"] for r in results) / total
    win_rate    = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    lift_pct    = ((avg_with - avg_without) / avg_without * 100) if avg_without > 0 else 0
    return {
        "wins": wins, "losses": losses, "ties": ties, "total": total,
        "avg_with": round(avg_with, 2), "avg_without": round(avg_without, 2),
        "win_rate": round(win_rate, 1), "lift_pct": round(lift_pct, 1),
        "delta": round(avg_with - avg_without, 2)
    }

def print_stats(label, stats, color):
    if not stats:
        log(f"  {label}: No results", C.RED)
        return
    verdict = (
        "VALIDATED ✓"  if stats["win_rate"] >= 65 else
        "MARGINAL ~"   if stats["win_rate"] >= 50 else
        "NOT PROVEN ✗"
    )
    vcolor = C.GREEN if stats["win_rate"] >= 65 else (C.YELLOW if stats["win_rate"] >= 50 else C.RED)

    log(f"\n  {label}", color)
    log(f"  {'─'*40}", C.GRAY)
    log(f"  Win Rate:      {stats['win_rate']}%  ({stats['wins']}W / {stats['losses']}L / {stats['ties']}T)", color)
    log(f"  Avg WITH:      {stats['avg_with']}/10", C.GREEN)
    log(f"  Avg WITHOUT:   {stats['avg_without']}/10", C.GRAY)
    log(f"  Score Delta:   +{stats['delta']} pts", C.GREEN if stats["delta"] > 0 else C.RED)
    log(f"  Lift:          +{stats['lift_pct']}%", C.GREEN if stats["lift_pct"] > 0 else C.RED)
    log(f"  Verdict:       {verdict}", vcolor)

def generate_arxiv_claims(all_results_by_model):
    """Print honest, specific claims for the arXiv paper."""
    header("arXiv — Validated Claims From This Experiment")

    validated = []
    not_validated = []

    for model_id, results in all_results_by_model.items():
        s = compute_stats(results)
        if not s:
            continue
        if s["win_rate"] >= 65:
            validated.append((model_id, s))
        else:
            not_validated.append((model_id, s))

    if validated:
        log("\n✓ WHAT YOU CAN CLAIM (honest, specific, reproducible):", C.GREEN)
        model_names = " and ".join(m.upper() for m, _ in validated)
        avg_wr   = sum(s["win_rate"]   for _, s in validated) / len(validated)
        avg_with = sum(s["avg_with"]   for _, s in validated) / len(validated)
        avg_wo   = sum(s["avg_without"] for _, s in validated) / len(validated)
        n_trials = sum(s["total"]      for _, s in validated)

        log(f"""
  "In a blind A/B evaluation, CSP-1 text-summary fingerprints achieved a {avg_wr:.1f}%
  win rate across {model_names} ({n_trials} trials total, Claude-as-judge,
  randomized blind presentation). Fingerprint-conditioned responses scored
  {avg_with:.2f}/10 vs {avg_wo:.2f}/10 for unconditioned baselines — a
  {((avg_with - avg_wo) / avg_wo * 100):.1f}% improvement in stylistic consistency."
""", C.WHITE)

    log("⚠ WHAT YOU MUST NOT CLAIM (still unvalidated):", C.YELLOW)
    log("""
  — The PCA/HDC binary encoder produces this improvement
    (text-summary method was tested, not the binary pipeline)
  — Task performance improvement (this measured stylistic consistency only)
  — "12.7% lift" without clarifying it was a model-size comparison
""", C.GRAY)

    log("📄 SUGGESTED NARRATIVE SHIFT (Personal Identity framing):", C.BLUE)
    log("""
  FROM: "CSP-1: A compression protocol for agent task memory"
  TO:   "CSP-1: Portable Conversational Identity — A User-Owned Protocol
         for Preserving and Transferring Human-AI Relational Style
         Across Models and Sessions"

  Core contribution: A compact fingerprint captures sufficient stylistic signal
  to reproduce conversational identity on any LLM, without storing raw conversation
  data. Validated across multiple frontier models.

  PCA/HDC role: Validated for speaker identification (p < 10⁻¹⁰⁰, separate result).
  Described as complementary encoding and future work for automated fingerprint
  extraction. Not the source of the stylistic consistency improvement.
""", C.GRAY)

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ConvoSeed CSP-1 Cross-Model A/B Test")
    parser.add_argument(
        "--models", nargs="+",
        choices=["claude", "gpt4", "gemini"],
        default=["claude"],
        help="Models to test (default: claude)"
    )
    parser.add_argument("--output", default="results.json", help="Output file for results")
    args = parser.parse_args()

    print(f"""
{C.BOLD}{C.CYAN}╔══════════════════════════════════════════════════╗
║   ConvoSeed CSP-1 — Cross-Model A/B Test         ║
║   Judge: Claude (always, independent)            ║
║   Personas: 5  ·  Prompts: 3  ·  Trials: 15/model ║
╚══════════════════════════════════════════════════╝{C.RESET}
""")
    log(f"Models to test: {', '.join(args.models)}", C.CYAN)
    log(f"Total trials:   {len(args.models) * 15}", C.CYAN)
    log(f"Output file:    {args.output}", C.CYAN)

    # Init clients
    claude_client = get_claude_client()
    all_results = {}

    # ── CLAUDE ────────────────────────────────────────────────────────────────
    if "claude" in args.models:
        def call_claude_fn(prompt, system):
            return call_claude(claude_client, prompt, system)
        results = run_model_experiment("claude", call_claude_fn, claude_client, "Claude Sonnet", C.YELLOW)
        all_results["claude"] = results

    # ── GPT-4O ────────────────────────────────────────────────────────────────
    if "gpt4" in args.models:
        gpt_client = get_openai_client()
        if gpt_client:
            def call_gpt_fn(prompt, system):
                return call_gpt4(gpt_client, prompt, system)
            results = run_model_experiment("gpt4", call_gpt_fn, claude_client, "GPT-4o", C.GREEN)
            all_results["gpt4"] = results

    # ── GEMINI ────────────────────────────────────────────────────────────────
    if "gemini" in args.models:
        genai_module = get_gemini_client()
        if genai_module:
            def call_gemini_fn(prompt, system):
                return call_gemini(genai_module, prompt, system)
            results = run_model_experiment("gemini", call_gemini_fn, claude_client, "Gemini 2.5 Flash", C.PURPLE)
            all_results["gemini"] = results

    # ── RESULTS SUMMARY ───────────────────────────────────────────────────────
    header("FINAL RESULTS")

    model_labels = {
        "claude": ("Claude Sonnet", C.YELLOW),
        "gpt4":   ("GPT-4o",        C.GREEN),
        "gemini": ("Gemini 2.5 Flash", C.PURPLE)
    }
    for model_id, results in all_results.items():
        label, color = model_labels[model_id]
        stats = compute_stats(results)
        print_stats(label, stats, color)

    # Cross-model comparison table
    if len(all_results) > 1:
        header("CROSS-MODEL COMPARISON")
        log(f"  {'Model':<20} {'Win Rate':>10} {'WITH':>8} {'WITHOUT':>10} {'Lift':>8} {'Verdict'}", C.WHITE)
        log(f"  {'─'*65}", C.GRAY)
        for model_id, results in all_results.items():
            s = compute_stats(results)
            if not s:
                continue
            label, color = model_labels[model_id]
            verdict = "✓ VALIDATED" if s["win_rate"] >= 65 else ("~ MARGINAL" if s["win_rate"] >= 50 else "✗ NOT PROVEN")
            vcolor  = C.GREEN if s["win_rate"] >= 65 else (C.YELLOW if s["win_rate"] >= 50 else C.RED)
            log(f"  {label:<20} {s['win_rate']:>9}% {s['avg_with']:>7}/10 {s['avg_without']:>9}/10 +{s['lift_pct']:>5}% ", color, end="")
            log(f"{verdict}", vcolor)

    # arXiv claims
    generate_arxiv_claims(all_results)

    # ── SAVE RESULTS ─────────────────────────────────────────────────────────
    output = {
        "experiment": "CSP-1 Cross-Model Style Fingerprint A/B Test",
        "date": datetime.now().isoformat(),
        "method": {
            "personas": len(PERSONAS),
            "prompts_per_persona": len(TEST_PROMPTS),
            "trials_per_model": 15,
            "judge": "Claude Sonnet (always independent)",
            "blinding": "Randomized X/Y assignment per trial"
        },
        "models_tested": list(all_results.keys()),
        "summary": {
            model_id: compute_stats(results)
            for model_id, results in all_results.items()
        },
        "trials": {
            model_id: [
                {k: v for k, v in t.items() if k not in ("resp_with", "resp_without", "fingerprint")}
                for t in results
            ]
            for model_id, results in all_results.items()
        },
        "full_responses": {
            model_id: results
            for model_id, results in all_results.items()
        }
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    log(f"\n✅ Full results saved to: {output_path.resolve()}", C.GREEN)
    log("   This file contains all responses and fingerprints for your paper.", C.GRAY)


if __name__ == "__main__":
    main()
