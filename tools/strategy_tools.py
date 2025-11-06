"""
strategyTools.py
----------------
Purpose
    Exposes a LangChain tool that the LLM can call at runtime to fetch live data
    from a backend API.

How it fits in the project
    - `main.py` binds this tool to the model, so the model can choose to call it
      when answering a question (tool calling).

Typical flow
    1) The model decides to call the tool `search_strategies`.
    2) The tool serializes the criteria to JSON.
    3) The tool posts to the API and returns the response as a string.

Notes for hackathon participants
    - You do NOT have to call this function directly — `main.py` handles tool binding.
"""

import os
import json
import requests
from langchain_core.tools import tool
from typing import Optional, Set, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from dotenv import load_dotenv
from models.criteria import AuditedCriteriaModel
import urllib3

# Temporarily disable Insecure request warning !! DO NOT USE IN PROD !!
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

BASE_URL = os.getenv("APPIA5_BASE_URL")
TOKEN = os.getenv("APPIA5_API_TOKEN")

def _headers():
    h = {"Accept": "application/json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


class StrategyTypeEnum(str, Enum):
    ADVANCE_PURCHASE = "ADVANCE_PURCHASE"
    AU_SETTING = "AU_SETTING"
    CLASS_NON_REOPENING = "CLASS_NON_REOPENING"
    COMPETITION_MATCHING = "COMPETITION_MATCHING"
    FINAL_AU_SETTING = "FINAL_AU_SETTING"
    INITIAL_GROUPING = "INITIAL_GROUPING"
    JOURNEY_SCORING = "JOURNEY_SCORING"
    LINKED_CLOSURE = "LINKED_CLOSURE"
    LINKED_DEPARTURE = "LINKED_DEPARTURE"
    LINKED_DEPARTURE_CLOSURE = "LINKED_DEPARTURE_CLOSURE"
    LINKED_RELATION = "LINKED_RELATION"
    OD_LINKED_RELATION = "OD_LINKED_RELATION"
    PRICE_CONSISTENCY = "PRICE_CONSISTENCY"
    SPILL_CONTROL = "SPILL_CONTROL"
    SPOILAGE_ALLOCATION = "SPOILAGE_ALLOCATION"


class StrategyCriteriaModel(AuditedCriteriaModel):
    """
    StrategyCriteria fields (Java) mirrored in Python.

    - codes: Set<String>
    - codeMatch: String  (prefix/wildcard semantics depend on backend)
    - name: String
    - description: String
    - valid: Boolean
    - types: Set<StrategyType>   (use names from StrategyTypeEnum)
    - journeyGroups: Set<String>
    - onDemandStrategyListOwners: Set<String>
    """
    codes: Optional[Set[str]] = Field(default=None)
    codeMatch: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    valid: Optional[bool] = Field(default=None)
    types: Optional[Set[StrategyTypeEnum]] = Field(
        default=None,
        description="Enum names of StrategyType, e.g. {'AU_SETTING','FINAL_AU_SETTING'}"
    )
    journeyGroups: Optional[Set[str]] = Field(default=None)
    onDemandStrategyListOwners: Optional[Set[str]] = Field(default=None)

# POST /api/strategies/search
@tool("search_strategies", args_schema=StrategyCriteriaModel)
def search_strategies(**kwargs) -> str:
    """
    Calls POST /api/strategies/search with optional StrategyCriteria.

    - Retrieves a collection of strategies by a given criteria
    - Returns a JSON string of the search results.
    """
    if not BASE_URL:
        print("ERROR: APPIA5_BASE_URL is not set.")
        return "ERROR: APPIA5_BASE_URL is not set."

    url = f"{BASE_URL}/api/strategies/search"

    # Build criteria from kwargs
    criteria = StrategyCriteriaModel(**kwargs)
    tmp = criteria.model_dump(exclude_none=True)
    
    criteria_dict: Optional[Dict[str, Any]] = None
    if tmp: 
        if "types" in tmp and tmp["types"] is not None:
            tmp["types"] = [t.value for t in tmp["types"]]
        criteria_dict = tmp

    try:
        if criteria_dict is None:
            resp = requests.post(url, headers=_headers(), verify=False)
        else:
            resp = requests.post(url, json=criteria_dict, headers=_headers(), verify=False)

        resp.raise_for_status()

        try:
            return json.dumps(resp.json())
        except ValueError:
            print( resp.text[:10000])
            return resp.text[:10000]

    except requests.exceptions.RequestException as e:
        print(f"ERROR: {e}")
        return f"ERROR: {e}"