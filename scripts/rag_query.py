#!/usr/bin/env python3
"""
scripts/rag_query.py
--------------------
Load a JSON file with trains, build a natural-language query, run the agent (RAG) and save a structured JSON result.

Usage:
  python3 scripts/rag_query.py --input output/sample_trains.json --output output/rag_agent_result.json

The script will attempt to use the existing `agent` from `main.py`. If the agent call fails (for example missing API keys),
it falls back to a deterministic comparator (max/min load_factor).
"""

import argparse
import json
import os
import re
import sys
import time

# Make project root importable when this script is executed from the scripts/ folder
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def build_query(trains: list[dict]) -> str:
    parts = [f"journey key = {t['journey_key']} and load factor = {t['load_factor']}" for t in trains]
    joined = " and another train with ".join(parts) if len(parts) > 1 else parts[0]
    # More explicit phrasing for the model + request structured JSON
    query = (
        f"I have the following trains: {', '.join(parts)}. "
        "Which one is the best and which one is the worst and why? "
        "Please respond as a single JSON object exactly with fields: \n"
        "{\"best\": {\"journey_key\": int, \"load_factor\": float, \"rationale\": str}, "
        "\"worst\": {\"journey_key\": int, \"load_factor\": float, \"rationale\": str}, "
        "\"citations\": [str]}"
    )
    return query


def try_agent_query(agent, query: str, timeout: float = 30.0) -> str:
    """Call agent.stream like main.py and collect the streamed text."""
    input_data = {"messages": [{"role": "user", "content": query}]}
    collected = []
    start = time.time()
    try:
        for chunk in agent.stream(input_data, stream_mode="updates"):
            # chunk is a mapping of step->data
            for step, data in chunk.items():
                # data['messages'][-1].content_blocks contains pieces; join any 'text' fields
                blocks = data['messages'][-1].content_blocks
                for b in blocks:
                    text = b.get('text') or b.get('content') or ''
                    if text:
                        collected.append(text)
            if time.time() - start > timeout:
                break
    except Exception as e:
        raise

    return "".join(collected)


def extract_first_json(text: str):
    # Try to extract the first {...} block
    m = re.search(r"\{.*?\}\s*$", text, re.S)
    if not m:
        m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return None
    candidate = m.group(0)
    try:
        return json.loads(candidate)
    except Exception:
        return None


def deterministic_result(trains: list[dict]):
    best = max(trains, key=lambda t: t['load_factor'])
    worst = min(trains, key=lambda t: t['load_factor'])
    out = {
        "best": {"journey_key": best['journey_key'], "load_factor": best['load_factor'], "rationale": "Higher load factor => better utilization"},
        "worst": {"journey_key": worst['journey_key'], "load_factor": worst['load_factor'], "rationale": "Lower load factor => poorer utilization"},
        "citations": []
    }
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="output/sample_trains.json")
    parser.add_argument("--output", type=str, default="output/rag_agent_result.json")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        trains = json.load(f)

    query = build_query(trains)

    # Try to use the agent from main.py
    result = None
    try:
        from main import get_agent
        print('Constructing agent...')
        agent = get_agent()
        print('Running agent RAG query...')
        full_text = try_agent_query(agent, query, timeout=args.timeout)
        print('Agent returned text (truncated):', full_text[:400])
        parsed = extract_first_json(full_text)
        if parsed is not None:
            result = parsed
        else:
            print('Agent did not return JSON — falling back to deterministic result')
    except Exception as e:
        print('Agent call failed or unavailable:', str(e))

    if result is None:
        result = deterministic_result(trains)

    # Ensure output dir exists
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    # Also write a human-readable summary next to the JSON result
    txt_out = os.path.splitext(args.output)[0] + '.txt'
    lines = []
    lines.append('RAG QUERY RESULT')
    lines.append('===============')
    lines.append(f"Best: journey_key={result['best']['journey_key']} (load_factor={result['best']['load_factor']})")
    lines.append(f"  Rationale: {result['best'].get('rationale','')}")
    lines.append('')
    lines.append(f"Worst: journey_key={result['worst']['journey_key']} (load_factor={result['worst']['load_factor']})")
    lines.append(f"  Rationale: {result['worst'].get('rationale','')}")
    lines.append('')
    lines.append('Citations:')
    for c in result.get('citations', []):
        lines.append(f' - {c}')

    with open(txt_out, 'w') as f:
        f.write('\n'.join(lines))

    print('Saved result to', args.output)
    print('Saved human-readable summary to', txt_out)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
