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
