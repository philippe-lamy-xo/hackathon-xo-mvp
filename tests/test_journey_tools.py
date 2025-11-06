import json

from tools.journey_tools import extract_journey_info


def test_heuristic_extraction():
    text = "JourneyId: 12345\nScore: 2.5\nReason: On-time performance improved.\nSolution: Keep current setup."
    out = extract_journey_info(text)
    j = json.loads(out)
    assert j["journey_id"] == "12345"
    assert j["score"] == "2.5"
    assert "improved" in j["reason"].lower()
    assert j["confidence"] == "heuristic"


def test_fallback_extraction():
    text = "The journey 789 had a severe issue. The reason was a late crew and delays. We recommend reassigning staff as a solution to limit future impacts."
    out = extract_journey_info(text)
    j = json.loads(out)
    # Fallback may not find a journey_id but should capture reason/solution as low-confidence
    assert j["confidence"] == "low"
    assert j["reason"] is None or isinstance(j["reason"], str)


def test_empty_input():
    text = "   \n  \n"
    out = extract_journey_info(text)
    j = json.loads(out)
    assert j["confidence"] == "low"
    assert j.get("excerpt") is not None


def test_refine_with_mock_llm():
    from tools.journey_tools import refine_extraction_with_llm

    sample = "Journey 42 had issues with crew."

    def mock_predict(prompt: str) -> str:
        # Return a valid JSON object embedded in text
        return 'Here is the JSON:\n{"journey_id": "42", "score": "-1.5", "reason": "crew shortage", "solution": "reassign crew"}'

    out = refine_extraction_with_llm(sample, llm_predict=mock_predict)
    assert out is not None
    obj = json.loads(out)
    assert obj["journey_id"] == "42"
    assert obj["confidence"] == "llm"


def test_extractor_uses_llm_when_low_confidence():
    from tools.journey_tools import extract_journey_info

    sample = "Journey 42 had issues with crew."

    def mock_predict(prompt: str) -> str:
        return '{"journey_id":"42","score":"-1.5","reason":"crew shortage","solution":"reassign crew"}'

    out = extract_journey_info(sample, llm_predict=mock_predict)
    assert out is not None
    obj = json.loads(out)
    assert obj["confidence"] == "llm"
    assert obj["score_numeric"] == -1.5
