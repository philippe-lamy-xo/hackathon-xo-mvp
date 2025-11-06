"""
journey_tools.py
----------------
Tool to extract structured journey information (journey id, score, reason, solution)
from an arbitrary text or document. This is implemented as a small wrapper that
uses a deterministic heuristic first (regex/key search) and falls back to a
lightweight LLM prompt if heuristics fail. The function returns JSON string.

This file is intentionally simple and dependency-free so it can run in the
hackathon environment without extra installation. It can be replaced later
with a proper @tool-decorated LangChain tool if needed.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Optional

# LangChain tool support
try:
    from pydantic import BaseModel
    from langchain.tools import tool
except Exception:  # If langchain/pydantic are not installed, we still keep the core functionality.
    BaseModel = None
    tool = None


def _heuristic_extract(text: str) -> Optional[Dict[str, str]]:
    """Try fast heuristic extraction using regex and keywords.

    Looks for lines like:
      JourneyId: 12345
      Score: -3.2
      Reason: ...
      Solution: ...

    Returns None if heuristics find nothing useful.
    """
    # Normalize line endings
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None

    # try to find key:value patterns
    data = {}
    kv_re = re.compile(r"^(?P<key>journey[_ ]?id|id|score|reason|solution|raison|raisonnement)\s*[:=]\s*(?P<val>.+)$", re.I)
    for line in lines:
        m = kv_re.match(line)
        if m:
            key = m.group("key").lower()
            val = m.group("val").strip()
            # normalize keys
            if "journey" in key or key == "id":
                data["journey_id"] = val
            elif "score" in key:
                data["score"] = val
            elif "reason" in key or "raison" in key:
                data.setdefault("reason", val)
            elif "solution" in key:
                data.setdefault("solution", val)

    # Also try inline patterns like "score = -2.5" inside text
    if "score" not in data:
        m = re.search(r"score\s*[=:]\s*([-+]?[0-9]*\.?[0-9]+)", text, re.I)
        if m:
            data["score"] = m.group(1)

    if data:
        return data
    return None


def extract_journey_info(text: str, llm_predict: Optional[callable] = None) -> str:
    """Extract journey information and return a JSON string.

    Output schema:
      {
        "journey_id": "<string or null>",
        "score": "<string or null>",
        "reason": "<string or null>",
        "solution": "<string or null>",
        "confidence": "heuristic|low"
      }

    The function first runs a fast heuristic. If nothing is found, it uses a
    conservative fallback that picks a short excerpt for human review and marks
    confidence as 'low'.
    """
    # 1) Heuristic pass
    heur = _heuristic_extract(text)
    if heur:
        # ensure keys exist
        out = {
            "journey_id": heur.get("journey_id", None),
            "score": heur.get("score", None),
            "reason": heur.get("reason", None),
            "solution": heur.get("solution", None),
            "confidence": "heuristic",
        }
        # validate/coerce
        out = _coerce_and_validate(out)
        return json.dumps(out, ensure_ascii=False)

    # 2) Fallback: simple extractor that tries to guess with keywords and context
    # This is intentionally conservative: we don't hallucinate, only pick short
    # spans near likely keywords.
    lower = text.lower()
    out = {"journey_id": None, "score": None, "reason": None, "solution": None}

    # Journey id: look for 'journey' + digits
    m = re.search(r"journey[^0-9]{0,8}([0-9]{3,})", lower)
    if m:
        out["journey_id"] = m.group(1)

    # Score: nearest number after 'score' or stand-alone pattern
    m = re.search(r"score[^0-9\-+]{0,6}([-+]?[0-9]*\.?[0-9]+)", lower)
    if m:
        out["score"] = m.group(1)
    else:
        # try standalone numeric patterns that are short
        m2 = re.search(r"\b([-+]?[0-9]*\.?[0-9]{1,3})\b", lower)
        if m2:
            out["score"] = m2.group(1)

    # reason: grab sentence with 'reason' or 'because' or french 'raison'
    reason_match = re.search(r"([^.\n]{0,200}(reason|because|raison)[^.\n]{0,200})", text, re.I)
    if reason_match:
        out["reason"] = reason_match.group(1).strip()

    # solution: look for lines containing 'solution', 'fix', 'recommend'
    sol_match = re.search(r"([^.\n]{0,200}(solution|fix|recommend|recommendation|proposed)[^.\n]{0,200})", text, re.I)
    if sol_match:
        out["solution"] = sol_match.group(1).strip()

    confidence = "low"
    # if we found at least one meaningful value, keep the fallback output
    if any([out["journey_id"], out["score"], out["reason"], out["solution"]]):
        result = {**out, "confidence": confidence}
        result = _coerce_and_validate(result)
        # if low confidence and an llm_predict is provided, try to refine
        if result.get("confidence") == "low" and llm_predict:
            refined = refine_extraction_with_llm(text, llm_predict=llm_predict)
            if refined:
                try:
                    parsed = json.loads(refined)
                    parsed = _coerce_and_validate(parsed)
                    return json.dumps(parsed, ensure_ascii=False)
                except Exception:
                    return refined
        return json.dumps(result, ensure_ascii=False)

    # Nothing found: return minimal JSON with excerpt for human inspection
    excerpt = text.strip()[:400]
    result = {
        "journey_id": None,
        "score": None,
        "reason": None,
        "solution": None,
        "confidence": "low",
        "note": "no structured data found; see excerpt",
        "excerpt": excerpt,
    }
    result = _coerce_and_validate(result)
    # If LLM caller provided, attempt to refine
    if llm_predict:
        refined = refine_extraction_with_llm(text, llm_predict=llm_predict)
        if refined:
            try:
                parsed = json.loads(refined)
                parsed = _coerce_and_validate(parsed)
                return json.dumps(parsed, ensure_ascii=False)
            except Exception:
                return refined
    return json.dumps(result, ensure_ascii=False)


def _coerce_and_validate(payload: Dict[str, Optional[str]]) -> Dict:
    """Normalize keys and coerce score to float when possible.

    Returns a payload dict with:
      - journey_id as string or None
      - score as string if original (keeps string) and numeric converted stored in 'score_numeric'
      - reason, solution, confidence
    """
    out = dict(payload)
    # Normalize empty strings to None
    for k in ["journey_id", "score", "reason", "solution"]:
        v = out.get(k)
        if isinstance(v, str) and v.strip() == "":
            out[k] = None

    # Coerce score to float if possible and add numeric key
    score = out.get("score")
    score_num = None
    if score is not None:
        try:
            score_num = float(str(score).strip())
        except Exception:
            score_num = None
    out["score_numeric"] = score_num
    return out




# ---------------------------------------------------------------------------
# LangChain tool wrapper (optional)
# ---------------------------------------------------------------------------
if BaseModel and tool:
    class JourneyToolArgs(BaseModel):
        text: str


    @tool("extract_journey_info", args_schema=JourneyToolArgs, description="Extract journey_id, score, reason and solution from text and return JSON.")
    def extract_journey_info_tool(text: str) -> str:
        """Tool wrapper for LangChain agents. Returns the same JSON string as extract_journey_info."""
        return extract_journey_info(text)


def refine_extraction_with_llm(text: str, llm_predict: Optional[callable] = None) -> Optional[str]:
        """Try to refine/complete the extraction using an LLM.

        Parameters:
            - text: original document/text to analyze
            - llm_predict: optional callable that accepts a single prompt string and returns the LLM's reply string.

        Returns:
            - JSON string (same schema as extract_journey_info) if LLM provided and returns valid JSON; otherwise None.

        Notes:
            - This helper does not call external APIs by default. Provide `llm_predict` to enable an actual LLM call.
            - Use a strict prompt in the caller to force JSON output.
        """
        if not llm_predict:
                return None

        # Build a strict prompt asking for JSON output
        prompt = (
                "You are a precise data extractor. Given the following text, extract exactly the fields 'journey_id', 'score', 'reason', 'solution'. "
                "Return only valid JSON with these keys (use null when unknown). Do not add any explanation.\n\n"
                f"TEXT:\n{text}\n\n"
                "Output JSON example: {\n  \"journey_id\": null,\n  \"score\": null,\n  \"reason\": null,\n  \"solution\": null\n}"
        )

        try:
                reply = llm_predict(prompt)
                # Attempt to parse reply; be liberal and search for first JSON object
                m = re.search(r"(\{[\s\S]*\})", reply)
                if m:
                        jtext = m.group(1)
                        obj = json.loads(jtext)
                        # ensure the expected keys exist
                        final = {
                                "journey_id": obj.get("journey_id"),
                                "score": obj.get("score"),
                                "reason": obj.get("reason"),
                                "solution": obj.get("solution"),
                                "confidence": "llm",
                        }
                        return json.dumps(final, ensure_ascii=False)
        except Exception:
                return None

        return None


if __name__ == "__main__":
    sample = """
    JourneyId: 12345
    Score: -3.4
    Reason: Large delay caused by late arrival from previous leg.
    Solution: Reallocate rolling stock, notify operations.
    """
    print(extract_journey_info(sample))
