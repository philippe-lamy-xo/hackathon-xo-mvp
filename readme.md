# AI RAG Template (LangChain + HuggingFace + Openai + Chroma)

This is a **Retrieval-Augmented Generation** (RAG) starter template.
It loads documents from the `data/` folder, stores them in a Chroma vector database, and answers questions by retrieving relevant chunks and passing them to a Large Language Model (LLM).

---

## Project Structure

```
data/                     # Place your PDFs and TXT files here
chroma/                   # Auto-generated Chroma vector database
ingest.py                 # Script to load documents into Chroma
main.py                   # Script to query the database via RAG
get_embedding_function.py # Selects the embedding model
readme.md                 # This file
```

## Prerequisites

- **Python 3.10+**

---

## Installation

### 1. Create a Virtual Environment
## TPAD (Train Performance Alerting Dashboard)

This repository contains the TPAD (Train Performance Alerting Dashboard) hackathon prototype. The goal of TPAD is to extract structured journey information from free-form text, ingest supporting documents into a local RAG index, and provide an agent and small demo UI that outputs structured JSON suitable for dashboards or downstream automation.

The rest of this README focuses exclusively on what we built during the hackathon, how it works, and how to use the agent prompt (with examples).

### What we built (high level)

- `tools/journey_tools.py` — a deterministic-first extractor that returns a strict JSON string with fields: `journey_id`, `score`, `reason`, `solution`, `confidence`, and `score_numeric`. The extractor uses fast heuristics (regex/key:value), a conservative fallback, and an optional LLM refinement helper (`refine_extraction_with_llm`) for low-confidence cases.
- `tools/rag_tools.py` — a retrieval helper that opens the Chroma vector store (persisted in `chroma/`), performs similarity searches, and formats the retrieved snippets for the agent context.
- `tools/tools.py` — registry of tools wired into the agent (including the extractor and retrieval tool).
- `main.py` — runtime entrypoint and `get_agent()` factory that builds the RAG-aware agent on demand (avoids import-time side effects).
- `ingest.py` — ingestion script to split documents under `data/`, compute embeddings with the local HF model configured in `get_embedding_function.py`, and persist them to Chroma in `chroma/`.
- `scripts/rag_query.py` — programmatic runner that queries the agent over a list of trains (JSON input) and writes structured JSON plus a human-readable result to `output/`.
- `scripts/extract_from_csv.py` — batch CSV -> JSONL extractor that uses `tools/journey_tools.extract_journey_info`.
- `scripts/server.py` + `public/journey_dashboard_demo.html` — a tiny HTTP server and static demo UI that serves `output/journeys.jsonl` at `/api/journeys` and visualizes top/bottom journeys.
- `scripts/start_server.sh`, `scripts/stop_server.sh`, `scripts/status_server.sh` — demo server management scripts.
- `tests/test_journey_tools.py` and `scripts/run_unit_tests.py` — small unit tests and a test runner for the extractor heuristics and mocked LLM path.

### Output schema

All extractor outputs and agent-produced structured results follow a compact JSON shape (returned as a JSON string by the extractor):

{
   "journey_id": string|null,
   "score": string|null,
   "reason": string|null,
   "solution": string|null,
   "confidence": "heuristic"|"low"|"llm",
   "score_numeric": number|null
}

The agent (`scripts/rag_query.py` or `main.py` when invoked programmatically) wraps this and produces an overall result describing the best/worst journeys and supporting citations.

### How the extractor works (short explanation)

1. Heuristic pass: fast regex/key:value detection for lines like `JourneyId: 12345`, `Score: -3.4`, `Reason: ...`, `Solution: ...`. If the heuristic finds meaningful values, it returns `confidence: "heuristic"`.
2. Conservative fallback: if heuristics fail, the extractor searches for short spans near keywords (`score`, `reason`, `solution`) and extracts short sentences as candidate values. The result is marked `confidence: "low"`.
3. Optional LLM refinement: when `llm_predict` callable is provided and the result is `confidence: "low"`, the extractor calls `refine_extraction_with_llm` which prompts the LLM to return strict JSON. The helper attempts to parse and normalize the returned JSON; if successful, `confidence` becomes `"llm"`.

This design minimizes hallucinations by preferring deterministic heuristics and only calling an LLM when necessary.

### How to use the agent prompt — examples

Below are pragmatic examples showing how to call the agent and the extractor via CLI and programmatically. Replace the placeholder values (API keys, etc.) as needed.

1) CLI: quick RAG question (uses `main.py`)

```bash
python3 main.py "I have a train with journey key = 100 and load factor = 0.8 and another train with journey key = 200 and load factor = 0.5, which one is the best and which one is the worst and why"
```

Expected behavior: `main.py` will construct the agent (via `get_agent()`), run the query using the RAG retrieval for context, and print a human-readable answer plus (optionally) a JSON file in `output/` if configured. The agent chooses the best/worst train by comparing `load_factor` (higher is generally worse for load; adjust your scoring rules in `scripts/rag_query.py` or the agent prompt if you want a different behavior).

2) Programmatic: use `scripts/rag_query.py` on sample input

Input example (create `output/sample_trains.json`):

```json
[
   {"journey_key": 100, "load_factor": 0.8, "description": "Journey 100 late due to congestion"},
   {"journey_key": 200, "load_factor": 0.5, "description": "Journey 200 running normally"}
]
```

Run the query runner:

```bash
python3 scripts/rag_query.py --input output/sample_trains.json --output output/rag_agent_result.json
```

This writes structured JSON to `output/rag_agent_result.json` and a human-readable summary to `output/rag_agent_result.txt`.

3) Direct extractor usage (CSV batch)

```bash
python3 scripts/extract_from_csv.py data/sample_journeys.csv output/journeys.jsonl
```

This runs `tools/journey_tools.extract_journey_info` on each CSV row and appends JSONL records to `output/journeys.jsonl` (each line contains the original `source_id` and the extracted `extracted` JSON object).

4) Using LLM refinement (programmatic example)

In Python, provide an `llm_predict` callable that sends a strict prompt to your LLM and returns its response text. Example pseudocode:

```python
from tools.journey_tools import extract_journey_info

def my_predict(prompt: str) -> str:
      # Use your chat client here (OpenAI/Azure/etc.) and return the reply text
      return chat_client.predict(prompt)

text = "Some noisy log text mentioning JourneyId: 12345 and a score of -4.2 because of late arrival."
json_str = extract_journey_info(text, llm_predict=my_predict)
obj = json.loads(json_str)
```

The helper `refine_extraction_with_llm` asks the LLM to return only valid JSON with the required keys. The extractor will attempt to parse any JSON object returned by the model.

### Agent prompt guidance (how to craft the prompt)

The agent's prompt focuses on producing structured, conservative decisions with citations. When creating or customizing the prompt (in `prompt_template.py` or `main.py`), prefer these rules:

- Ask the agent to prefer deterministic evidence from the retrieved documents (cite chunk locations or snippet text) before applying heuristics.
- Ask the agent to return a brief rationale and, if a structured JSON is requested, to emit a valid JSON object with only the required fields.
- When expecting strict JSON, include an exact schema example and instruct the model to "Return only valid JSON and nothing else." This reduces hallucination.

Example minimal strict prompt for the LLM refinement helper (used internally by `refine_extraction_with_llm`):

"You are a precise extractor. Given the following text, extract exactly the fields 'journey_id', 'score', 'reason', 'solution'. Return only valid JSON with these keys (use null when unknown). Do not add any explanation."

### Tests

Run the small test runner for the extractor:

```bash
python3 scripts/run_unit_tests.py
```

The tests validate heuristic extraction patterns, fallback behavior, and a mocked LLM path.

### Running the ingestion (optional, if you want RAG)

1. Put your documents (PDF/TXT) into `data/`.
2. Run ingestion to populate the local Chroma store:

```bash
python3 ingest.py --reset
```

The persistence directory is `chroma/` (excluded from git). The embeddings implementation is selected in `get_embedding_function.py`.

### Where to look in the code

- `tools/journey_tools.py` — deterministic extractor and LLM refinement helper.
- `tools/rag_tools.py` — retrieval helper that queries the Chroma store.
- `main.py` — agent factory (`get_agent`) and CLI entrypoint.
- `scripts/rag_query.py` — programmatic runner that inputs a list of trains and writes structured outputs.

### Next steps and suggestions

- If you want production-ready behavior: add JSON schema validation for LLM outputs and unit tests that assert strict JSON shape across common documents.
- Add CI to run `scripts/run_unit_tests.py` on push.
- If you want the demo UI removed, archive `public/journey_dashboard_demo.html` and the `scripts/*.sh` helper scripts; otherwise keep them for demos.

---

If you'd like, I can now: (A) add a small README subsection that includes the exact agent prompt used by `scripts/rag_query.py` and `main.py`, (B) archive the demo/deploy files into an `archive/` directory, or (C) add JSON schema validation and tests for the extractor outputs. Tell me which you'd prefer and I'll proceed.
- tests/test_journey_tools.py — unit tests (heuristic, fallback, LLM mock, extractor+LLM)

- deploy/tpad-server.service, deploy/README.md — systemd unit + instructions
