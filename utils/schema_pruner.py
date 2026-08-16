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


def match_tables_with_fingerprints(
    question: str,
    fingerprints: dict[str, str],
    top_k: int = 7
) -> list[str]:
    """
    Pillar 1: Precision Schema Retrieval using Column Fingerprints.
    Indexes 'Table: name. Columns: col1, col2...' for all 3,000+ tables.
    Solves both the cryptic name problem and the hidden column problem.
    """
    if not fingerprints:
        return []
    if len(fingerprints) <= top_k:
        return list(fingerprints.keys())

    scores: dict[str, float] = {}
    q_lower = question.lower()
    q_words = set(re.findall(r'\w+', q_lower))

    # Try dense semantic embedding
    try:
        q_vec = _embed_text(question)
        for tname, cols in fingerprints.items():
            cache_key = f"fp_{tname}_{hash(cols)}"
            if cache_key in _EMBEDDINGS_CACHE:
                t_vec = _EMBEDDINGS_CACHE[cache_key]
            else:
                summary = f"Table: {tname}. Columns: {cols}"
                t_vec = _embed_text(summary)
                _EMBEDDINGS_CACHE[cache_key] = t_vec

            sim = _cosine_similarity(q_vec, t_vec)
            
            # Exact table name in question boost
            if tname.lower() in q_lower:
                sim += 0.4
            
            # Specific column name in question boost
            col_tokens = set(re.findall(r'\w+', cols.lower()))
            overlap = q_words.intersection(col_tokens)
            if overlap:
                sim += 0.15 * len(overlap)
                
            scores[tname] = sim
    except Exception:
        # Fast lexical hybrid scoring
        for tname, cols in fingerprints.items():
            t_lower = tname.lower()
            score = 0.0
            if t_lower in q_lower:
                score += 4.0
            col_tokens = set(re.findall(r'\w+', cols.lower()))
            overlap = q_words.intersection(col_tokens)
            score += len(overlap) * 2.0
            scores[tname] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [t[0] for t in ranked[:top_k]]


def match_relevant_table_names(
    question: str, 
    all_table_names: list[str], 
    top_k: int = 7
) -> list[str]:
    """
    Given a list of table names, match the top_k most relevant.
    """
    # Create simple identity fingerprints {table_name: table_name}
    fp = {t: t for t in all_table_names}
    return match_tables_with_fingerprints(question, fp, top_k=top_k)


def expand_with_foreign_key_bridges(
    selected_tables: list[str],
    fk_graph: dict[str, set[str]],
    max_bridges: int = 2
) -> list[str]:
    """
    Pillar 2: Foreign Key Graph Auto-Expansion.
    If Table A and Table B are selected but not directly connected by a foreign key,
    finds an intermediate bridge table C (e.g. 'appointments' linking 'doctors' & 'billing')
    and includes it automatically so Gemini never writes broken/hallucinated JOINs.
    """
    if not fk_graph or len(selected_tables) < 2:
        return selected_tables

    current_set = set(selected_tables)
    added_bridges = []

    # Check all pairs in selected_tables
    for i in range(len(selected_tables)):
        for j in range(i + 1, len(selected_tables)):
            t1 = selected_tables[i]
            t2 = selected_tables[j]

            # If t1 and t2 already share a direct FK, no bridge needed
            if t2 in fk_graph.get(t1, set()) or t1 in fk_graph.get(t2, set()):
                continue

            # Search for a 1-hop bridge table C that connects both t1 and t2
            t1_neighbors = fk_graph.get(t1, set())
            t2_neighbors = fk_graph.get(t2, set())
            common_neighbors = t1_neighbors.intersection(t2_neighbors)

            for bridge in common_neighbors:
                if bridge not in current_set and len(added_bridges) < max_bridges:
                    added_bridges.append(bridge)
                    current_set.add(bridge)

    return selected_tables + added_bridges


def get_effective_schema(
    question: str,
    engine,
    all_table_names: list[str],
    pre_fetched_schemas: dict[str, str] = None,
    table_fingerprints: dict[str, str] = None,
    fk_graph: dict[str, set[str]] = None,
    csv_tables: dict = None,
    top_k: int = 7
) -> tuple[str, list[str]]:
    """
    Anti-Hallucination Hybrid Schema Engine:
    - Mode 1 (<= 150 tables): Fast in-memory Schema RAG + FK Auto-Expansion.
    - Mode 2 (> 150 to 3,000+ tables): Column Fingerprint Matching + On-Demand Targeted Column Fetching + FK Auto-Expansion.
    """
    from utils.connection_manager import fetch_columns_for_specific_tables

    # Mode 1: In-Memory Pre-Fetched Schema (<= 150 tables)
    if pre_fetched_schemas and len(pre_fetched_schemas) > 0:
        pruned_schema_str, matched_names = prune_schema(question, pre_fetched_schemas, top_k=top_k)
        if fk_graph:
            expanded_names = expand_with_foreign_key_bridges(matched_names, fk_graph)
            if len(expanded_names) > len(matched_names):
                # Pull in the extra bridge tables
                extra_schemas = [pre_fetched_schemas[t] for t in expanded_names if t in pre_fetched_schemas]
                return "\n\n".join(extra_schemas), expanded_names
        return pruned_schema_str, matched_names

    # Mode 2: On-Demand Just-In-Time Fetching (3,000+ tables)
    if table_fingerprints:
        matched_names = match_tables_with_fingerprints(question, table_fingerprints, top_k=top_k)
    else:
        matched_names = match_relevant_table_names(question, all_table_names, top_k=top_k)

    # Apply FK Bridge expansion
    if fk_graph:
        matched_names = expand_with_foreign_key_bridges(matched_names, fk_graph)

    dynamic_schemas = fetch_columns_for_specific_tables(engine, matched_names, csv_tables=csv_tables)
    final_schema_str = "\n\n".join(dynamic_schemas.values())
    return final_schema_str, matched_names

