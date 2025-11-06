from tools.journey_tools import extract_journey_info
from tools.rag_tools import retrieve_context
from tools.strategy_tools import search_strategies

# search_strategies is a tool that fetches data from appia5 endpoint.
# retrieve_context is a RAG tool that queries Chroma DB.
# code_interpreter allows to run code.
# OpenAPI supports multiple "native" tool types. See https://platform.openai.com/docs/guides/tools
TOOLS = [retrieve_context, search_strategies, extract_journey_info] + [
    {
        "type": "code_interpreter",
        "container": {"type": "auto"}
    }
]

# -----------------------------------------------------------------------------
# How to add another tool for appia5
# -----------------------------------------------------------------------------
# 1) Define a Pydantic args schema if needed (class MyToolArgs(BaseModel): ...).
# 2) Write a function that performs the work and returns a string/JSON string.
# 3) Decorate it with @tool("my_tool_name", args_schema=MyToolArgs).
# 4) Add it to TOOLS.
# 5) Ask questions naturally; the model may choose to call your tool if relevant.
#
# Keep tools small and predictable: clear inputs, clear outputs, clear errors.
#
# Check langchain documentation (available in readme).
