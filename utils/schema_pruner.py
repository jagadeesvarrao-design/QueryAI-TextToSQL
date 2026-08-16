"""
schema_pruner.py — Semantic Schema Pruning (Schema RAG) for QueryAI.
Embeds database table definitions and performs cosine similarity search 
against the user's natural language question to select only relevant tables.
"""
import os
import re
import numpy as np
from dotenv import load_dotenv

load_dotenv(override=True)

# Cache for table embeddings: {cache_key: np.array}
_EMBEDDINGS_CACHE = {}

# Try importing SDKs gracefully
_GENAI_NEW = None
_GENAI_LEGACY = None

try:
    from google import genai as _genai_new
    _GENAI_NEW = _genai_new
except Exception:
    pass

try:
    import google.generativeai as _genai_legacy
    _GENAI_LEGACY = _genai_legacy
except Exception:
    pass


def _get_api_key():
    return os.getenv("GEMINI_API_KEY", "")


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot_product / (norm1 * norm2))


def _embed_text(text_content: str, model: str = "models/text-embedding-004") -> np.ndarray:
    """Generate vector embedding using Gemini API with fallback across SDKs."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing for embedding generation.")

    # Try new google.genai SDK first
    if _GENAI_NEW is not None:
        try:
            client = _GENAI_NEW.Client(api_key=api_key)
            res = client.models.embed_content(
                model="text-embedding-004",
                contents=text_content
            )
            return np.array(res.embeddings[0].values, dtype=np.float32)
        except Exception:
            pass

    # Try legacy google.generativeai SDK
    if _GENAI_LEGACY is not None:
        try:
            _GENAI_LEGACY.configure(api_key=api_key)
            res = _GENAI_LEGACY.embed_content(
                model=model,
                content=text_content,
                task_type="retrieval_query"
            )
            return np.array(res["embedding"], dtype=np.float32)
        except Exception:
            pass

    raise RuntimeError("Could not generate vector embedding via Gemini API.")


def _keyword_similarity(question: str, table_name: str, schema_text: str) -> float:
    """Fast lexical overlap fallback if vector embedding fails."""
    q_words = set(re.findall(r'\w+', question.lower()))
    target_words = set(re.findall(r'\w+', f"{table_name} {schema_text}".lower()))
    
    if not q_words or not target_words:
        return 0.0
    
    # Exact table name match receives high boost
    score = 0.0
    if table_name.lower() in q_words:
        score += 3.0
    
    overlap = q_words.intersection(target_words)
    score += len(overlap) / len(q_words)
    return score


def prune_schema(
    question: str,
    table_schemas: dict[str, str],
    top_k: int = 7
) -> tuple[str, list[str]]:
    """
    Given a question and a dictionary of {table_name: table_schema_str},
    retrieve only the top_k most relevant tables using Semantic Vector Search.
    
    Returns:
        (pruned_schema_str, list_of_selected_table_names)
    """
    total_tables = len(table_schemas)
    
    # If the database has 6 or fewer tables, no pruning needed — return full schema
    if total_tables <= 6 or total_tables <= top_k:
        full_schema = "\n\n".join(table_schemas.values())
        return full_schema, list(table_schemas.keys())

    scores: dict[str, float] = {}
    
    # Try semantic embedding similarity first
    try:
        q_vec = _embed_text(question)
        
        for table_name, schema_text in table_schemas.items():
            # Build semantic representation of table
            table_summary = f"Table name: {table_name}. Schema details: {schema_text}"
            cache_key = f"{table_name}_{hash(schema_text)}"
            
            if cache_key in _EMBEDDINGS_CACHE:
                table_vec = _EMBEDDINGS_CACHE[cache_key]
            else:
                table_vec = _embed_text(table_summary)
                _EMBEDDINGS_CACHE[cache_key] = table_vec
                
            sim = _cosine_similarity(q_vec, table_vec)
            
            # Boost if exact table name is mentioned in question
            if table_name.lower() in question.lower():
                sim += 0.25
                
            scores[table_name] = sim

    except Exception:
        # Graceful fallback: Lexical keyword scoring
        for table_name, schema_text in table_schemas.items():
            scores[table_name] = _keyword_similarity(question, table_name, schema_text)

    # Sort tables by score descending
    ranked_tables = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    selected_tables = [t[0] for t in ranked_tables[:top_k]]
    
    # Always preserve original order for consistency in prompt
    ordered_selected = [t for t in table_schemas.keys() if t in selected_tables]
    pruned_schema = "\n\n".join(table_schemas[t] for t in ordered_selected)
    
    return pruned_schema, ordered_selected


def match_relevant_table_names(
    question: str, 
    all_table_names: list[str], 
    top_k: int = 7
) -> list[str]:
    """
    Given 3,000+ table names, rank and match the top_k most relevant table names
    to the user's natural language question without needing column metadata.
    """
    if not all_table_names:
        return []
    if len(all_table_names) <= top_k:
        return list(all_table_names)

    scores: dict[str, float] = {}
    
    # Try vector embedding on table names
    try:
        q_vec = _embed_text(question)
        for tname in all_table_names:
            cache_key = f"name_{tname}"
            if cache_key in _EMBEDDINGS_CACHE:
                t_vec = _EMBEDDINGS_CACHE[cache_key]
            else:
                t_vec = _embed_text(f"Database table: {tname}")
                _EMBEDDINGS_CACHE[cache_key] = t_vec
                
            sim = _cosine_similarity(q_vec, t_vec)
            # Direct word match boost
            if tname.lower() in question.lower():
                sim += 0.5
            scores[tname] = sim
    except Exception:
        # Fast lexical keyword fallback
        q_lower = question.lower()
        q_words = set(re.findall(r'\w+', q_lower))
        for tname in all_table_names:
            t_lower = tname.lower()
            score = 0.0
            if t_lower in q_lower:
                score += 3.0
            t_words = set(re.findall(r'\w+', t_lower))
            overlap = q_words.intersection(t_words)
            score += len(overlap)
            scores[tname] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [t[0] for t in ranked[:top_k]]


def get_effective_schema(
    question: str,
    engine,
    all_table_names: list[str],
    pre_fetched_schemas: dict[str, str] = None,
    csv_tables: dict = None,
    top_k: int = 7
) -> tuple[str, list[str]]:
    """
    Hybrid Schema Engine:
    - If <= 150 tables and pre_fetched_schemas available: Uses fast in-memory Schema RAG.
    - If > 150 tables (3,000+ tables): Performs Just-In-Time On-Demand Column Fetching!
    """
    from utils.connection_manager import fetch_columns_for_specific_tables

    # Mode 1: In-Memory Pre-Fetched Schema (<150 tables)
    if pre_fetched_schemas and len(pre_fetched_schemas) > 0:
        return prune_schema(question, pre_fetched_schemas, top_k=top_k)

    # Mode 2: On-Demand Just-In-Time Fetching (3,000+ tables)
    matched_names = match_relevant_table_names(question, all_table_names, top_k=top_k)
    dynamic_schemas = fetch_columns_for_specific_tables(engine, matched_names, csv_tables=csv_tables)
    
    final_schema_str = "\n\n".join(dynamic_schemas.values())
    return final_schema_str, matched_names

