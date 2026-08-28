"""
gemini_client.py

Wywoluje Gemini API (google-genai, oficjalny SDK) zeby generowac lekcje
BEZPOSREDNIO w aplikacji, bez recznego kopiowania promptu do innego okna.

Posiada kaskadowy fallback: jesli wybrany model (np. gemini-3.7-flash)
jest chwilowo przeciazony (503 UNAVAILABLE), automatycznie przelacza sie
na gemini-3.6-flash lub gemini-3.1-flash-lite bez przerywania dzialania.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEFAULT_MODEL = "gemini-3.6-flash"
FALLBACK_ORDER = ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-3.7-flash"]


def generate_lesson_text(
    api_key: str,
    prompt: str,
    model_id: str = DEFAULT_MODEL,
    max_retries_per_model: int = 2,
    retry_delay: float = 3.0,
) -> tuple[str, str]:
    """
    Wysyla prompt do Gemini i zwraca (tekst_odpowiedzi, uzyty_model).
    W razie bledu 503 lub przeciazenia automatycznie kaskadowo sprawdza
    kolejne modele z listy FALLBACK_ORDER.
    """
    from google import genai

    client = genai.Client(api_key=api_key)

    candidate_models = [model_id] + [m for m in FALLBACK_ORDER if m != model_id]
    last_error: Exception = RuntimeError("Brak odpowiedzi od zadnego z modeli Gemini.")

    for candidate in candidate_models:
        for attempt in range(max_retries_per_model):
            try:
                response = client.models.generate_content(model=candidate, contents=prompt)
                if response.text:
                    return response.text, candidate
                finish_reason = response.candidates[0].finish_reason if response.candidates else "brak"
                last_error = RuntimeError(f"Pusta odpowiedz od {candidate} (finish_reason: {finish_reason})")
            except Exception as e:
                last_error = e
                if attempt < max_retries_per_model - 1:
                    time.sleep(retry_delay)

    raise last_error


def generate_and_validate_lesson(
    api_key: str,
    prompt: str,
    language: str,
    known_lemmas: set,
    target_lemmas: list,
    min_target_occurrences: int = 2,
    model_id: str = DEFAULT_MODEL,
    max_repair_attempts: int = 2,
) -> tuple[str, str | None, dict, int, str]:
    """
    Generuje lekcje i automatycznie naprawia ja, jesli walidacja wykryje
    naruszenia - wysyla liste bledow z powrotem do modelu i prosi o
    przepisanie (do max_repair_attempts razy).

    Zwraca (oczyszczony_tekst, wybrane_miejsce_lub_None, wynik_walidacji,
    ile_naprawek_wykonano, uzyty_model).
    """
    from validator import validate_generated_text
    from prompt_builder import build_fix_prompt, extract_setting_from_text

    raw_text, used_model = generate_lesson_text(api_key, prompt, model_id=model_id)
    cleaned_text, setting_name = extract_setting_from_text(raw_text)
    result = validate_generated_text(cleaned_text, language, known_lemmas, target_lemmas, min_target_occurrences)
    attempts_used = 0

    while not result["ok"] and attempts_used < max_repair_attempts:
        fix_prompt = build_fix_prompt(
            raw_text, result["violations"], result["missing_targets"], min_target_occurrences
        )
        try:
            raw_text, used_model = generate_lesson_text(api_key, fix_prompt, model_id=used_model)
            cleaned_text, setting_name = extract_setting_from_text(raw_text)
            result = validate_generated_text(cleaned_text, language, known_lemmas, target_lemmas, min_target_occurrences)
            attempts_used += 1
        except Exception:
            break

    return cleaned_text, setting_name, result, attempts_used, used_model
