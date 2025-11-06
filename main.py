"""
main.py
-------
Runs a Retrieval-Augmented Generation (RAG) query using Chroma DB and Azure OpenAI.

Steps:
1. Create a retrieval tool that wraps the Chroma vector database
2. Build an agent with access to retrieval + other tools
3. Stream the agent's response with full tool-calling support

Usage:
    python main.py "Your question here"
"""

import argparse
import os
import time
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from prompt_template import SYSTEM_PROMPT
from tools.tools import TOOLS

load_dotenv()


def get_agent():
    """Construct and return the LangChain agent instance.

    This is exported so other scripts can import and create the agent
    on demand (avoids side-effects at import time).
    """
    # Azure OpenAI chat client
    model = ChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        model="gpt-5-mini"
    )

    agent = create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT
    )

    return agent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="The query.")
    args = parser.parse_args()
    query = args.query
    # Build agent and run the query
    agent = get_agent()
    query_rag(agent, query)

def query_rag(agent, query: str):
    """
    Run a RAG query using the agent.
    Streams the response and displays timing.
    """
    start_time = time.time()

    input_data = {"messages": [{"role": "user", "content": query}]}

    # See available stream modes in langchain docs
    for chunk in agent.stream(input_data, stream_mode="updates"):
        for step, data in chunk.items():
            print(f"\nstep: {step}")
            print(f"content: {data['messages'][-1].content_blocks}")

    end_time = time.time()

    additional_info = f"\n---\nResponded in: {end_time - start_time:.2f} seconds"

    print(additional_info)


if __name__ == "__main__":
    main()
