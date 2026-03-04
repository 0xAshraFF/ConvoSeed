import { useState } from "react";

const ANTHROPIC_API = "https://api.anthropic.com/v1/messages";
const MODEL = "claude-sonnet-4-6";

// ── 5 Personas ────────────────────────────────────────────────────────────────
const PERSONAS = [
  {
    id: "researcher",
    name: "Academic Researcher",
    summary: `This person writes with measured precision and intellectual rigor. Sentences are structured carefully, often building from premise to conclusion. They prefer hedged language ('it appears', 'evidence suggests') over declarative statements. Vocabulary is technical but accessible. They ask clarifying questions before answering. Paragraphs are organized with clear logical flow. Tone is collaborative and curious rather than authoritative.`,
    testPrompt: "What do you think about the current state of AI research?",
  },
  {
    id: "startup",
    name: "Startup Founder",
    summary: `This person communicates with high-energy urgency. Short punchy sentences. Heavy use of action verbs. They think in frameworks and analogies. Skip pleasantries — get to the point fast. Use startup vocabulary: 'ship it', 'move the needle', '10x'. Bulleted thinking. Confident, sometimes overconfident. Always focused on what's next, not what happened.`,
    testPrompt: "How should I prioritize my next 3 months?",
  },
  {
    id: "teacher",
    name: "Patient Teacher",
    summary: `This person explains things by building from fundamentals. They never assume prior knowledge. Use analogies to everyday objects. Check for understanding mid-explanation. Warm, encouraging tone. Celebrate small wins. Break complex ideas into numbered steps. Ask 'does that make sense?' frequently. Never make the learner feel stupid for not knowing something.`,
    testPrompt: "Can you explain how neural networks work?",
  },
  {
    id: "philosopher",
    name: "Philosophical Thinker",
    summary: `This person responds to questions with deeper questions. They reframe problems rather than solving them directly. Dense, layered sentences. Comfortable with ambiguity and contradiction. Frequently reference historical ideas without naming them directly. Use words like 'perhaps', 'one might argue', 'and yet'. End responses with open-ended observations rather than conclusions.`,
    testPrompt: "Is artificial intelligence truly intelligent?",
  },
  {
    id: "engineer",
    name: "Systems Engineer",
    summary: `This person thinks in systems, constraints, and tradeoffs. Precise technical vocabulary. Never hand-wave over implementation details. Always ask 'what are the failure modes?' Structure answers as: problem → constraints → options → recommendation. Use concrete numbers wherever possible. Skeptical of solutions that seem too simple. Footnote-style caveats at the end.`,
    testPrompt: "How would you design a system to handle 1 million users?",
  },
];

// ── API call ──────────────────────────────────────────────────────────────────
async function callClaude(systemPrompt, userPrompt) {
  const res = await fetch(ANTHROPIC_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 300,
      system: systemPrompt,
      messages: [{ role: "user", content: userPrompt }],
    }),
  });
  const data = await res.json();
  return data.content?.[0]?.text || "[no response]";
}

// ── Judge call ────────────────────────────────────────────────────────────────
async function judgeResponses(personaSummary, responseA, responseB, prompt) {
  const judgePrompt = `You are a blind evaluator assessing which AI response better matches a target writing style.

TARGET STYLE:
${personaSummary}

QUESTION ASKED:
${prompt}

RESPONSE A:
${responseA}

RESPONSE B:
${responseB}

Which response better matches the target style? Consider: vocabulary, sentence structure, tone, level of detail, and personality.

Reply with ONLY: "A" or "B" followed by one sentence explaining why.`;

  const result = await callClaude("You are a precise, impartial evaluator.", judgePrompt);
  const winner = result.trim().startsWith("A") ? "A" : "B";
  return { winner, reasoning: result };
}

// ── Main component ────────────────────────────────────────────────────────────
export default function StyleABTest() {
  const [results, setResults] = useState([]);
  const [running, setRunning] = useState(false);
  const [currentTrial, setCurrentTrial] = useState("");
  const [done, setDone] = useState(false);

  const runAllTrials = async () => {
    setRunning(true);
    setResults([]);
    setDone(false);
    const allResults = [];

    for (let rep = 0; rep < 3; rep++) {
      for (const persona of PERSONAS) {
        setCurrentTrial(`${persona.name} (rep ${rep + 1}/3)`);

        // Randomize which is WITH and which is WITHOUT
        const fpFirst = Math.random() > 0.5;

        const [withResp, withoutResp] = await Promise.all([
          callClaude(persona.summary + "\n\nAnswer naturally in your style.", persona.testPrompt),
          callClaude("You are a helpful assistant.", persona.testPrompt),
        ]);

        const responseA = fpFirst ? withResp : withoutResp;
        const responseB = fpFirst ? withoutResp : withResp;

        const judgment = await judgeResponses(
          persona.summary,
          responseA,
          responseB,
          persona.testPrompt
        );

        const fpWon =
          (judgment.winner === "A" && fpFirst) ||
          (judgment.winner === "B" && !fpFirst);

        allResults.push({
          persona: persona.name,
          rep: rep + 1,
          fpFirst,
          judgeWinner: judgment.winner,
          fpWon,
          reasoning: judgment.reasoning,
          withResp: withResp.slice(0, 120) + "...",
          withoutResp: withoutResp.slice(0, 120) + "...",
        });

        setResults([...allResults]);
        await new Promise((r) => setTimeout(r, 500));
      }
    }

    setRunning(false);
    setDone(true);
  };

  const fpWins = results.filter((r) => r.fpWon).length;
  const total = results.length;
  const winRate = total > 0 ? Math.round((fpWins / total) * 100) : 0;

  return (
    <div style={{ fontFamily: "monospace", padding: 24, maxWidth: 860, margin: "0 auto" }}>
      <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>
        ConvoSeed V2 — Style Preservation A/B Test
      </h2>
      <p style={{ color: "#555", fontSize: 13 }}>
        Blind randomized evaluation. 5 personas × 3 reps = 15 trials. Claude-as-judge.
        Tests whether CSP-1 summary fingerprints preserve writing style vs no fingerprint.
      </p>

      <button
        onClick={runAllTrials}
        disabled={running}
        style={{
          padding: "10px 24px",
          background: running ? "#999" : "#1a1a1a",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          cursor: running ? "not-allowed" : "pointer",
          fontSize: 14,
          marginBottom: 20,
        }}
      >
        {running ? `▶ Running: ${currentTrial}` : "▶ Run Style A/B Test (15 trials)"}
      </button>

      {total > 0 && (
        <div style={{ background: "#f5f5f5", padding: 16, borderRadius: 8, marginBottom: 20 }}>
          <div style={{ fontSize: 22, fontWeight: "bold" }}>
            FP Win Rate: {winRate}% ({fpWins}/{total})
          </div>
          {done && (
            <div style={{ marginTop: 8, color: winRate >= 70 ? "#1a7a1a" : "#aa3300" }}>
              {winRate >= 70
                ? "✓ STYLE PRESERVATION VALIDATED — fingerprints significantly outperform baseline"
                : winRate >= 50
                ? "⚠ Marginal improvement — more trials recommended"
                : "✗ No clear improvement — fingerprints not effective for style"}
            </div>
          )}
        </div>
      )}

      {results.map((r, i) => (
        <div
          key={i}
          style={{
            border: "1px solid #ddd",
            borderRadius: 6,
            padding: 12,
            marginBottom: 10,
            borderLeft: `4px solid ${r.fpWon ? "#1a7a1a" : "#aa3300"}`,
          }}
        >
          <div style={{ fontWeight: "bold", marginBottom: 4 }}>
            {r.fpWon ? "✓" : "✗"} {r.persona} — Rep {r.rep}
          </div>
          <div style={{ fontSize: 12, color: "#555", marginBottom: 4 }}>
            Judge picked: {r.judgeWinner} (FP was {r.fpFirst ? "A" : "B"}) →{" "}
            {r.fpWon ? "FP WON" : "BASELINE WON"}
          </div>
          <div style={{ fontSize: 11, color: "#777" }}>{r.reasoning}</div>
        </div>
      ))}

      {done && (
        <div
          style={{
            background: "#1a1a1a",
            color: "#fff",
            padding: 20,
            borderRadius: 8,
            marginTop: 20,
            fontFamily: "monospace",
          }}
        >
          <div style={{ fontSize: 16, marginBottom: 12 }}>━━ VERDICT (V2 — Style Preservation) ━━</div>
          <div>FP win rate: {winRate}% ({fpWins}/{total} trials)</div>
          <div>Personas tested: 5</div>
          <div>Reps per persona: 3</div>
          <div>Judge: Claude-as-judge (blind, randomized presentation)</div>
          <div style={{ marginTop: 12, color: winRate >= 70 ? "#7aff7a" : "#ffaa7a" }}>
            {winRate >= 70
              ? "✓ VALIDATED — Style fingerprints reliably outperform no-context baseline"
              : "⚠ INCONCLUSIVE — Results below 70% threshold"}
          </div>
        </div>
      )}
    </div>
  );
}
