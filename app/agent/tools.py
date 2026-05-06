"""
RestorAI - Agent Tools (Tool Engineering with Pydantic)

Tools exposed to the LangGraph agent:
    1. analyze_furniture_image       : Google Gemini vision analysis
    2. search_restoration_knowledge  : RAG over the ChromaDB knowledge base (Lab 2)
    3. search_web_for_products       : Mock product / retailer lookup
    4. order_products                : HIGH-RISK action gated by HITL

Configuration:
    OPENAI_API_KEY    - required for embeddings + chat model
    GOOGLE_API_KEY    - optional, enables real Gemini vision
    CHROMA_DB_PATH    - optional, overrides default ./chroma_db location
                        (Docker compose mounts a volume here)

Author: Abdullah Noor - 2022029
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
import google.generativeai as genai
from chromadb.config import Settings
from langchain_core.tools import tool
from openai import OpenAI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_chroma_path() -> Path:
    """
    Resolve the ChromaDB persistent directory.

    Priority:
        1. CHROMA_DB_PATH environment variable (used by Docker container)
        2. <repo-root>/chroma_db                (local development)
    """
    env_path = os.getenv("CHROMA_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2] / "chroma_db"


def _make_chroma_client():
    """
    Build a ChromaDB client.

    * If ``CHROMA_HOST`` is set (e.g. in docker-compose), connect to the remote
      ChromaDB server via HTTP - this is the multi-service production layout.
    * Otherwise, fall back to a local PersistentClient (used during dev / tests
      and when running ``ingest_data`` against a mounted volume).
    """
    settings = Settings(anonymized_telemetry=False)
    host = os.getenv("CHROMA_HOST")
    if host:
        port = int(os.getenv("CHROMA_PORT", "8000"))
        return chromadb.HttpClient(host=host, port=port, settings=settings)
    return chromadb.PersistentClient(path=str(_resolve_chroma_path()), settings=settings)


# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------

class VisionAnalysisInput(BaseModel):
    image_path: str = Field(description="Path to the furniture image file (JPG/PNG/JPEG).")
    analysis_focus: Optional[str] = Field(
        default="general",
        description="Focus of analysis: 'general' | 'material' | 'damage' | 'condition'.",
    )


class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="Natural-language query for the restoration knowledge base.")
    content_filter: Optional[str] = Field(
        default=None,
        description="Optional: 'identification' | 'techniques' | 'safety' | 'products' | 'finishing'.",
    )
    safety_only: Optional[bool] = Field(
        default=False, description="If True, only return high-priority safety information."
    )
    n_results: Optional[int] = Field(default=3, description="Number of results (1-5).")


class WebSearchInput(BaseModel):
    query: str = Field(description="Search query for current product info, prices or availability.")
    focus: Optional[str] = Field(
        default="products",
        description="Search focus: 'products' | 'prices' | 'tutorials' | 'suppliers'.",
    )


class OrderProductsInput(BaseModel):
    items: List[str] = Field(description="Products / items to order.")
    shipping_address: str = Field(description="Shipping address (use 'LOCAL_TEST' in demos).")
    max_budget_usd: Optional[float] = Field(default=None, description="Optional max budget (USD).")
    notes: Optional[str] = Field(default=None, description="Optional notes / instructions.")


# ---------------------------------------------------------------------------
# Tool 1: Vision Analysis (Google Gemini)
# ---------------------------------------------------------------------------

@tool("analyze_furniture_image", args_schema=VisionAnalysisInput)
def analyze_furniture_image(image_path: str, analysis_focus: str = "general") -> str:
    """
    Analyze a furniture image to identify materials, damage, and condition using
    Google Gemini Vision. Use this when the user has supplied an image.
    Returns a JSON string with material / finish / damage / condition / recommendations.
    """
    try:
        if not os.path.exists(image_path):
            return json.dumps({
                "error": f"Image file not found: {image_path}",
                "material": "Unknown",
                "damage": ["Cannot analyze - file not found"],
            })

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return json.dumps({
                "error": "GOOGLE_API_KEY not set",
                "material": "Unknown - API key missing",
                "damage": ["Cannot analyze without API key"],
                "note": "Set GOOGLE_API_KEY for real Gemini vision analysis.",
            })

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompts = {
            "general": (
                "Analyze this furniture image. Return JSON with keys: "
                "material, finish, damage, condition, restoration_feasibility."
            ),
            "material": "Focus on wood species, construction (solid vs veneer), finish type. Return JSON.",
            "damage": "Focus on damage assessment (type, severity, location, root cause). Return JSON.",
            "condition": "Assess structural integrity, finish condition, hardware, restoration effort. Return JSON.",
        }
        prompt = prompts.get(analysis_focus, prompts["general"])

        import PIL.Image
        img = PIL.Image.open(image_path)
        response = model.generate_content([prompt, img])

        result: Dict[str, Any] = {
            "analysis_type": analysis_focus,
            "raw_analysis": response.text,
            "image_path": image_path,
        }
        try:
            import re
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                result.update(json.loads(match.group()))
        except Exception:
            pass

        return json.dumps(result, indent=2)

    except Exception as exc:
        return json.dumps({
            "error": str(exc),
            "material": "Analysis failed",
            "damage": [f"Error: {exc}"],
        })


# ---------------------------------------------------------------------------
# Tool 2: Knowledge Base Search (RAG)
# ---------------------------------------------------------------------------

@tool("search_restoration_knowledge", args_schema=KnowledgeSearchInput)
def search_restoration_knowledge(
    query: str,
    content_filter: Optional[str] = None,
    safety_only: bool = False,
    n_results: int = 3,
) -> str:
    """
    Search the restoration knowledge base (ChromaDB) for repair techniques,
    safety information, material identification or product recommendations.
    Returns a JSON string with ranked results, metadata and similarity scores.
    """
    try:
        client = _make_chroma_client()
        try:
            collection = client.get_collection(name="restoration_knowledge")
        except Exception:
            # In a fresh HTTP-mode container the collection may not exist yet -
            # create it (idempotent).
            collection = client.get_or_create_collection(name="restoration_knowledge")

        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        emb = openai_client.embeddings.create(
            model="text-embedding-3-small", input=query
        ).data[0].embedding

        where_filter: Optional[Dict[str, Any]] = None
        if safety_only:
            where_filter = {"safety_level": "high_caution"}
        elif content_filter:
            where_filter = {"content_category": content_filter}

        n_results = max(1, min(5, n_results))
        results = collection.query(
            query_embeddings=[emb], n_results=n_results, where=where_filter
        )

        formatted = {
            "query": query,
            "filters_applied": {"content_filter": content_filter, "safety_only": safety_only},
            "num_results": len(results["ids"][0]),
            "results": [],
        }
        for i in range(len(results["ids"][0])):
            formatted["results"].append({
                "rank": i + 1,
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "relevance_score": 1 - results["distances"][0][i],
            })
        return json.dumps(formatted, indent=2)

    except Exception as exc:
        return json.dumps({
            "error": str(exc),
            "query": query,
            "results": [],
            "note": "Make sure the knowledge base has been ingested (python -m app.ingestion.ingest_data).",
        })


# ---------------------------------------------------------------------------
# Tool 3: Web Search (mock product database)
# ---------------------------------------------------------------------------

_MOCK_PRODUCT_DB: Dict[str, Dict[str, Any]] = {
    "wood glue": {
        "products": ["Titebond Original Wood Glue", "Titebond II Premium", "Gorilla Wood Glue"],
        "retailers": ["Home Depot", "Lowe's", "Amazon", "Ace Hardware"],
        "price_range": "$4-$12",
        "availability": "Widely available",
    },
    "wood filler": {
        "products": ["Minwax Wood Filler", "Elmer's Wood Filler", "Famowood Wood Filler"],
        "retailers": ["Home Depot", "Lowe's", "Walmart", "Amazon"],
        "price_range": "$5-$15",
        "availability": "Widely available",
    },
    "shellac": {
        "products": ["Zinsser Bulls Eye Shellac", "Shellac Flakes", "Behlen Shellac"],
        "retailers": ["Home Depot", "Rockler", "Woodcraft", "Amazon"],
        "price_range": "$8-$25",
        "availability": "Available at hardware and woodworking stores",
    },
    "polyurethane": {
        "products": ["Minwax Polyurethane", "Varathane", "General Finishes"],
        "retailers": ["Home Depot", "Lowe's", "Menards", "Amazon"],
        "price_range": "$10-$30",
        "availability": "Widely available",
    },
    "mineral spirits": {
        "products": ["Klean-Strip Mineral Spirits", "Crown Mineral Spirits", "Jasco"],
        "retailers": ["Home Depot", "Lowe's", "Ace Hardware", "AutoZone"],
        "price_range": "$8-$15",
        "availability": "Widely available",
    },
    "tung oil": {
        "products": ["Minwax Tung Oil", "Watco Tung Oil", "Hope's Pure Tung Oil"],
        "retailers": ["Home Depot", "Lowe's", "Rockler", "Amazon"],
        "price_range": "$12-$35",
        "availability": "Available at hardware and specialty woodworking stores",
    },
}


@tool("search_web_for_products", args_schema=WebSearchInput)
def search_web_for_products(query: str, focus: str = "products") -> str:
    """
    Look up products / retailers / approximate prices for restoration items.
    Uses an offline mock database so the tool works without external API keys.
    Returns a JSON string with matched categories, products and retailers.
    """
    q = query.lower()
    out: Dict[str, Any] = {"search_query": query, "focus": focus, "results": []}

    for key, info in _MOCK_PRODUCT_DB.items():
        if key in q or any(p.lower() in q for p in info["products"]):
            out["results"].append({
                "category": key.title(),
                "products": info["products"],
                "where_to_buy": info["retailers"],
                "price_range": info["price_range"],
                "availability": info["availability"],
            })

    if not out["results"]:
        out["results"].append({
            "note": "No specific product match found",
            "suggestion": "Try searching for: 'furniture restoration supplies near me'",
            "general_retailers": ["Home Depot", "Lowe's", "Ace Hardware", "Rockler", "Woodcraft"],
            "online_options": ["Amazon", "Woodworker's Supply", "Lee Valley Tools"],
        })
    return json.dumps(out, indent=2)


# ---------------------------------------------------------------------------
# Tool 4: Order Products (HIGH-RISK - HITL gated)
# ---------------------------------------------------------------------------

@tool("order_products", args_schema=OrderProductsInput)
def order_products(
    items: List[str],
    shipping_address: str,
    max_budget_usd: Optional[float] = None,
    notes: Optional[str] = None,
) -> str:
    """
    HIGH-RISK action: place an order for restoration items. In this educational
    project the tool only writes a local JSON record - it never performs a real
    purchase - but it is still treated as high-risk and gated by HITL approval.
    Returns a JSON string with the order record path and details.
    """
    orders_dir = Path(os.getenv("ORDERS_DIR", "./orders"))
    orders_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "items": items,
        "shipping_address": shipping_address,
        "max_budget_usd": max_budget_usd,
        "notes": notes,
        "status": "CREATED_LOCAL_RECORD_ONLY",
    }
    filename = f"order_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
    order_path = orders_dir / filename
    order_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return json.dumps({
        "ok": True,
        "message": "Order record created locally (no real purchase was made).",
        "order_file": str(order_path),
        "order": payload,
    }, indent=2)


# ---------------------------------------------------------------------------
# KnowledgeBase singleton (used by direct callers / tests)
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """Singleton ChromaDB connection used by direct callers and test scripts."""

    _instance: Optional["KnowledgeBase"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        try:
            self.chroma_client = _make_chroma_client()
            self.collection = self.chroma_client.get_collection(name="restoration_knowledge")
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self._initialized = True
        except Exception as exc:
            print(f"Warning: Could not connect to knowledge base: {exc}")
            self._initialized = False

    def search(
        self,
        query: str,
        content_filter: Optional[str] = None,
        safety_only: bool = False,
        n_results: int = 3,
    ) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Knowledge base not initialized", "results": []}
        try:
            emb = self.openai_client.embeddings.create(
                model="text-embedding-3-small", input=query
            ).data[0].embedding

            where_filter: Optional[Dict[str, Any]] = None
            if safety_only:
                where_filter = {"safety_level": "high_caution"}
            elif content_filter:
                where_filter = {"content_category": content_filter}

            results = self.collection.query(
                query_embeddings=[emb], n_results=n_results, where=where_filter
            )

            formatted: Dict[str, Any] = {
                "query": query,
                "filters": {"content_filter": content_filter, "safety_only": safety_only},
                "num_results": len(results["ids"][0]),
                "results": [],
            }
            for i in range(len(results["ids"][0])):
                formatted["results"].append({
                    "rank": i + 1,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "relevance_score": round(1 - results["distances"][0][i], 3),
                })
            return formatted
        except Exception as exc:
            return {"error": str(exc), "query": query, "results": []}


# ---------------------------------------------------------------------------
# Tool list exported to LangGraph
# ---------------------------------------------------------------------------

TOOLS = [
    analyze_furniture_image,
    search_restoration_knowledge,
    search_web_for_products,
    order_products,
]
