import os
import re
import json

from anthropic import Anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

ANALYSIS_SCHEMA = """Return ONLY a single valid JSON object, no markdown fences, no commentary, matching exactly this shape:
{
 "hallucination_risk": <0-100 integer, higher = more hallucinated>,
 "trust_score": <0-100 integer, higher = more trustworthy>,
 "verdict": "<one of: Reliable | Partially Reliable | Hallucination Detected>",
 "verdict_detail": "<one sentence explaining the verdict>",
 "claims": [ {"text": "<the claim as stated>", "status": "<correct|incorrect|uncertain>", "risk": "<low|medium|high>", "explanation": "<short reason>"} ],
 "highlighted_response": [ {"text": "<verbatim segment of the response>", "type": "<correct|suspicious|hallucination|neutral>"} ],
 "hallucination_type": "<e.g. Factual Hallucination, Temporal Hallucination, Numerical Hallucination, Citation Hallucination, None Detected>",
 "confidence_pct": <0-100, how confidently/assertively the response is phrased>,
 "correctness_pct": <0-100, your estimate of actual factual accuracy>,
 "supporting_evidence": [ {"text": "<short fact backing a correct claim>", "reliability": <0-100>} ],
 "contradicting_evidence": [ {"text": "<short fact contradicting an incorrect claim>", "reliability": <0-100>} ],
 "verification_signals": [ {"label": "Knowledge Base Check", "pct": <0-100>}, {"label": "Internal Consistency Check", "pct": <0-100>}, {"label": "Temporal / Date Check", "pct": <0-100>} ],
 "source_reliability": [ {"type": "Government / Official Sources", "score": <0-100>}, {"type": "Peer-Reviewed Research", "score": <0-100>}, {"type": "General Encyclopedic (e.g. Wikipedia)", "score": <0-100>}, {"type": "Unattributed / Unknown", "score": <0-100>} ]
}
Rules: "highlighted_response" segments concatenated (with original spacing) must reconstruct the full response text. "contradicting_evidence" is an empty array if nothing is contradicted. "source_reliability" scores are general reliability heuristics for that category of source, not specific citations for this answer. Keep every string concise. Output nothing except the JSON object."""


def _text_of(message) -> str:
    return "".join(block.text for block in message.content if block.type == "text").strip()


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def generate_answer(question: str) -> str:
    """Have Claude answer the question directly, so there's a real response to audit."""
    message = _client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=(
            "Answer the user's question directly and naturally in 2-3 sentences, the way a "
            "typical AI assistant would. Do not mention verification, accuracy, or hedge excessively."
        ),
        messages=[{"role": "user", "content": question}],
    )
    return _text_of(message)


def analyze_response(question: str, response_text: str) -> dict:
    """Run the hallucination-detection pass over a question/response pair."""
    user_message = (
        f'Question: "{question}"\n\n'
        f'Response to audit: "{response_text}"\n\n'
        f"{ANALYSIS_SCHEMA}"
    )
    message = _client.messages.create(
        model=MODEL,
        max_tokens=1400,
        system=(
            "You are HalluciGuard AI's verification engine, an expert fact-checker. You analyze "
            "an AI-generated answer, extract every discrete factual claim, verify each one against "
            "your best knowledge, and score the response's reliability. Be precise and skeptical."
        ),
        messages=[{"role": "user", "content": user_message}],
    )
    raw = _text_of(message)
    return json.loads(_strip_fences(raw))
