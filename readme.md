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

```bash
python -m venv .venv
```

### 2. Activate the Virtual Environment

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
./.venv/Scripts/activate
```

### 3. Install dependencies

Project dependencies are listed in the requirements.txt file.

To install them, run the following command:

```bash
pip install -r requirements.txt
```

If needed, you can add new dependencies to the file and re-run the command to install them.

### 4. Create a .env file

```.env
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
APPIA5_BASE_URL=
APPIA5_API_TOKEN=
```

## Ingesting Data

Place your documents in the `data/` folder (create it if it does not already exist), then run:

```bash
python ingest.py --reset
```

- `--reset` clears the database before re-ingesting.
- Without `--reset`, only new documents will be added.

---

## Asking Questions

Once data is ingested, ask a question:

```bash
python main.py "What is Appia?"
```

---

## Customization

- An LLM bases itself on two things to generate an answer:

  1. **The Context** → the information you provide to the model beforehand (documents ingested, split into chunks, transformed into embeddings and stored in a vector database, or conversation history). This is the knowledge base the model can draw from. \
     In this project, this is done via the _ingestion_ process. See [Ingesting Data](#ingesting-data)

  2. **The Prompt** → the actual question or instruction you send to the model at query time. This guides how the model should use the context (e.g., “Summarize this”, “Answer as a lawyer”, “Translate into Italian”). \
     In this project, the prompt is stored in the `PROMPT_TEMPLATE` variable.

- Read documentation: https://python.langchain.com/docs/integrations/chat/azure_chat_openai/

- Change embedding model in get_embedding_function.py:

```python
HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
```

- Adjust chunk size in ingest.py for more/less context.

---

## Resources

### Rag/Database

- [LangChain Document Loaders](https://python.langchain.com/docs/integrations/document_loaders/)
- [Chroma Vector DB](https://docs.trychroma.com/)

### Tool calling

- [Quickstart](https://docs.langchain.com/oss/python/langchain/quickstart)
- [Tools](https://docs.langchain.com/oss/python/langchain/tools)
- [Agent](https://docs.langchain.com/oss/python/langchain/agents)
- [Streaming](https://docs.langchain.com/oss/python/langchain/streaming)
- [OpenAi tools guide](https://platform.openai.com/docs/guides/tools?tool-type=remote-mcp)

---

## RAG Diagram

![Architecture Diagram](./public/diagram.svg "Architecture Diagram")

## Tool call Diagram

![Architecture Diagram](./public/tool_calls.svg "Tool call Diagram")

## TPAD (Train Performance Alerting Dashboard) — Hackathon additions

This repository was extended during the hackathon to add a small prototype that:
- Extracts structured journey information (journey_id, score, reason, solution) from free-form text.
- Provides a lightweight RAG-aware tool and optional LLM refinement helper.
- Adds CLI scripts for batch CSV extraction and a static demo dashboard with a small local HTTP server and management scripts.

The following sections explain what was added, how to run it, and what each file does.

### What I added (high level)
- `tools/journey_tools.py` — heuristic-first extractor + optional LangChain `@tool` wrapper and `refine_extraction_with_llm` helper.
- `scripts/demo_extract_journey.py` — CLI demo for the extractor.
- `scripts/extract_from_csv.py` — batch CSV -> JSONL extractor (writes `output/journeys.jsonl`).
- `scripts/server.py` — minimal HTTP server that serves static demo and an API at `/api/journeys` with query params.
- `public/journey_dashboard_demo.html` — small static dashboard UI that fetches the API and shows top/bottom journeys.
- `scripts/start_server.sh`, `scripts/stop_server.sh`, `scripts/status_server.sh` — start/stop/status helper scripts.
- `scripts/run_unit_tests.py` and `tests/test_journey_tools.py` — simple test runner + unit tests for extractor and LLM refinement (no pytest dependency required).
- `deploy/tpad-server.service` + `deploy/README.md` — example systemd unit and deploy instructions.

### Key features
- Heuristic-first deterministic extraction to avoid hallucination: the extractor tries fast regex/key:value detection first.
- Conservative fallback extraction captures short context spans when heuristics fail.
- Optional LLM refinement helper: pass an `llm_predict(prompt)` callable to `extract_journey_info(text, llm_predict=...)` and the extractor will call the LLM only when confidence is low. The helper asks the model to return strict JSON and parses it back.
- JSON output schema (returned as a JSON string):
   - journey_id, score, reason, solution, confidence (heuristic|low|llm), and `score_numeric` (float or null).
- Local API: `/api/journeys` supports query parameters: `top`, `bottom`, `limit`, `journey_id`, `min_confidence`.

### Files changed / added (concise)
- tools/journey_tools.py — extractor + optional LangChain wrapper + LLM helper + validation
- tools/tools.py — the new extractor was registered in the `TOOLS` list so the agent can call it
- scripts/demo_extract_journey.py — simple CLI demo
- scripts/extract_from_csv.py — CSV -> `output/journeys.jsonl`
- data/sample_journeys.csv — sample data used for the demo
- output/journeys.jsonl — sample generated output (created by the extraction script)
- public/journey_dashboard_demo.html — static visualization (fetches `/api/journeys?top=5`)
- scripts/server.py — static server + `/api/journeys` with query support
- scripts/start_server.sh, scripts/stop_server.sh, scripts/status_server.sh — process helpers
- scripts/run_unit_tests.py — test runner (no pytest required)
- tests/test_journey_tools.py — unit tests (heuristic, fallback, LLM mock, extractor+LLM)
- deploy/tpad-server.service, deploy/README.md — systemd unit + instructions

### Quick start (development)
1. (Optional) Create and activate a virtualenv and install dependencies from `requirements.txt` if you need langchain/embeddings features.

2. Run the CSV extraction to create demo JSONL:

```bash
python3 scripts/extract_from_csv.py data/sample_journeys.csv output/journeys.jsonl
```

3. Start the demo server (adopts an existing server process if present):

```bash
./scripts/start_server.sh
```

4. View the demo in your browser:

Open http://localhost:8000/ (the page at `public/journey_dashboard_demo.html` fetches `/api/journeys?top=5`)

5. Stop the server:

```bash
./scripts/stop_server.sh
```

6. Check server status and tail logs:

```bash
./scripts/status_server.sh
tail -f server.log
```

### API examples
- Get top 5 journeys (highest score):

```
curl "http://localhost:8000/api/journeys?top=5"
```

- Get bottom 3 journeys (lowest score):

```
curl "http://localhost:8000/api/journeys?bottom=3"
```

- Filter by journey id:

```
curl "http://localhost:8000/api/journeys?journey_id=2002"
```

### Using LLM refinement (example)
If you want the extractor to call an LLM when confidence is low, pass a callable that accepts a single prompt string and returns the model reply. Example (pseudocode):

```python
from tools.journey_tools import extract_journey_info

def my_predict(prompt: str) -> str:
      # call your ChatOpenAI/Azure client and return the reply string
      return chat_client.predict(prompt)

json_str = extract_journey_info(text, llm_predict=my_predict)
obj = json.loads(json_str)
```

The extractor will only call the LLM when heuristics don't provide high confidence results.

### Tests
- Run the bundled test runner (no pytest required):

```bash
python3 scripts/run_unit_tests.py
```

All tests in `tests/test_journey_tools.py` validate heuristic extraction, fallback behavior, and the mocked LLM path.

### Deploy as systemd service (optional)
See `deploy/README.md` for instructions. The example unit `deploy/tpad-server.service` shows a minimal unit file — edit the `User` and `WorkingDirectory` values for your environment before enabling.

### Next steps and ideas
- Wire real AppIA data ingestion and run the extractor over the nightly batch output.
- Expose more API filters (date ranges, score thresholds, confidence levels) and add authentication if exposing externally.
- Integrate the extractor tool into your LangChain agent flow so the agent can call it and use structured results in dialogues.
- Improve extraction coverage (multilingual patterns, richer heuristics) or use a strict JSON-output LLM refinement with schema validation.

If you want, I can now: (A) wire the extractor into your agent end-to-end with a real LLM call, (B) extend the dashboard UI with filters and CSV export, or (C) add CI (GitHub Actions) that runs the tests and a lint step on push.

