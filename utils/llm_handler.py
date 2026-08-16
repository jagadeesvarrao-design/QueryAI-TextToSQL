"""
llm_handler.py — Calls Google Gemini API to convert natural language to SQL.
"""
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

_MODELS = {}

# Models tried in order until one works — configurable via GEMINI_MODEL in .env
_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]


def _get_model(model_name: str = None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Please add it to your .env file."
        )
    genai.configure(api_key=api_key)

    preferred = model_name or os.getenv("GEMINI_MODEL", "").strip()
    models_to_try = ([preferred] + _FALLBACK_MODELS) if preferred else _FALLBACK_MODELS
    
    # De-duplicate while preserving order
    seen = set()
    models_to_try = [x for x in models_to_try if x and not (x in seen or seen.add(x))]

    last_err = None
    for m_name in models_to_try:
        if m_name in _MODELS:
            return _MODELS[m_name], m_name
        try:
            candidate = genai.GenerativeModel(m_name)
            # Quick smoke test
            candidate.generate_content("ping")
            _MODELS[m_name] = candidate
            print(f"[QueryAI] Configured model: {m_name}")
            return candidate, m_name
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(
        f"No working Gemini model found. Tried: {models_to_try}. Last error: {last_err}"
    )


SYSTEM_PROMPT = """You are an expert SQL assistant. Your job is to convert natural language questions into valid {dialect} SQL queries.

Rules:
1. Only output the raw SQL query — no explanations, no markdown, no code blocks.
2. The query MUST be valid {dialect} syntax. Use appropriate dialect-specific syntax (e.g. date/time functions, string concatenation, limit/offset, etc.) that matches {dialect}.
3. Use only the tables and columns provided in the schema below.
4. Use JOINs when needed to combine data across tables.
5. For aggregation questions, use GROUP BY with appropriate aggregate functions (COUNT, SUM, AVG, MAX, MIN).
6. Add ORDER BY and LIMIT clauses where appropriate for readability.
7. Column names are case-sensitive — use them exactly as shown.
8. If the question cannot be answered from the schema, return: SELECT 'Sorry, I cannot answer this from the available data.' AS message;

Database Schema:
{schema}
"""


from utils.schema_pruner import prune_schema


def generate_sql(
    user_question: str,
    schema: str | dict[str, str],
    dialect: str = "SQLite",
    model_name: str = None,
    top_k_tables: int = 7
) -> tuple[str, str, str]:
    """
    Convert a natural language question to SQL using Gemini.
    Automatically applies Semantic Schema Pruning (Schema RAG) if a dictionary
    of table schemas is provided.
    
    Returns:
        (sql_query, used_model_name, error_message)
    """
    try:
        # If schema is a dict of individual table definitions, prune it semantically
        if isinstance(schema, dict):
            final_schema, _ = prune_schema(user_question, schema, top_k=top_k_tables)
        else:
            final_schema = schema

        model, used_model = _get_model(model_name)
        prompt = SYSTEM_PROMPT.format(dialect=dialect, schema=final_schema) + f"\n\nUser Question: {user_question}"
        
        response = model.generate_content(prompt)
        raw_output = response.text.strip()
        
        # Clean up any accidental markdown code blocks
        sql = _clean_sql(raw_output)
        return sql, used_model, ""

    except ValueError as e:
        return "", "", str(e)
    except Exception as e:
        return "", "", f"Gemini API error: {str(e)}"


def _clean_sql(text: str) -> str:
    """Strip markdown code fences if Gemini accidentally includes them."""
    # Remove ```sql ... ``` or ``` ... ```
    text = re.sub(r"```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    return text.strip()
