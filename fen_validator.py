import json
import os
import chess
from openai import OpenAI

CACHE_FILE = "canonical_fens.json"
CONFIDENCE_THRESHOLD = 0.7

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def is_legal_fen(fen: str) -> bool:
    try:
        board = chess.Board(fen)
        return board.is_valid()
    except Exception:
        return False

def llm_conceptual_check(fen: str, concept: str) -> float:
    """
    Sends the FEN and concept to LLM to estimate conceptual match confidence (0–1).
    """
    prompt = f"""You are a chess instructor.
Given this FEN: {fen}
Does it accurately represent the concept "{concept}"?
Respond ONLY with a confidence number between 0 and 1."""

    try:
        api_key = os.getenv('OPENAI_API_KEY')
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        value = response.choices[0].message.content.strip()
        return float(value)
    except Exception as e:
        print(f"[ERROR] LLM check failed: {e}")
        return 0.0

def validate_and_cache_fen(fen: str, concept: str) -> bool:
    """
    Validates FEN through legality + conceptual check.
    Caches it if confidence ≥ threshold.
    """
    if not is_legal_fen(fen):
        print(f"[INVALID FEN] {concept}: {fen}")
        return False

    confidence = llm_conceptual_check(fen, concept)
    print(f"[CHECK] {concept}: confidence={confidence:.2f}")

    if confidence >= CONFIDENCE_THRESHOLD:
        cache = load_cache()
        cache[concept] = fen
        save_cache(cache)
        print(f"[CACHED] {concept} (confidence={confidence:.2f})")
        return True
    else:
        print(f"[REJECTED] {concept} (confidence={confidence:.2f})")
        return False
