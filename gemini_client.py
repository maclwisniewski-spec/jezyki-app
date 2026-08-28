"""
gemini_client.py

Wywoluje Gemini API (google-genai, oficjalny SDK) zeby generowac lekcje
BEZPOSREDNIO w aplikacji, bez recznego kopiowania promptu do innego okna.

Model domyslny: gemini-3.7-flash. Modele "preview" bywaja chwilowo
przeciazone (503 UNAVAILABLE) lub zwracaja pusta odpowiedz - stad
wbudowane ponawianie z odczekaniem i fallback na stabilniejszy model.
"""
from __future__ import annotations
import time

MODEL_ID = "gemini-3.7-flash"


def generate_lesson_text(api_key: str, prompt: str, model_id: str = MODEL_ID,
                          max_retries: int = 3, retry_delay: float = 15.0) -> str:
    """
    Wysyla prompt do Gemini i zwraca sam tekst odpowiedzi. Ponawia przy
    bledach 503 (chwilowe przeciazenie) lub pustej odpowiedzi, do
    max_retries razy. Rzuca wyjatkiem przy wyczerpaniu prob.
    """
    from google import genai
    from google.genai import errors

    client = genai.Client(api_key=api_key)
    last_error: Exception = RuntimeError(f"Brak odpowiedzi od modelu {model_id}")

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            if response.text:
                return response.text
            finish_reason = response.candidates[0].finish_reason if response.candidates else "brak"
            last_error = RuntimeError(f"Pusta odpowiedz od modelu {model_id} (finish_reason: {finish_reason})")
        except errors.ServerError as e:
            last_error = e

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    raise last_error


def generate_and_validate_lesson(
    api_key: str,
    prompt: str,
    language: str,
    known_lemmas: set,
    target_lemmas: list,
    min_target_occurrences: int = 2,
    model_id: str = MODEL_ID,
    fallback_model_id: str = "gemini-2.5-flash",
    max_repair_attempts: int = 2,
) -> tuple[str, str | None, dict, int]:
    """
    Generuje lekcje i automatycznie naprawia ja, jesli walidacja wykryje
    naruszenia - wysyla liste bledow z powrotem do modelu i prosi o
    przepisanie (do max_repair_attempts razy). Jesli model podstawowy
    (np. przeciazony 3.7-flash) zawiedzie od razu, przelacza sie na
    fallback_model_id zanim w ogole zwroci wynik.

    WAZNE: walidacja dziala na tekscie OCZYSZCZONYM z linii
    "MIEJSCE_AKCJI: ..." (patrz prompt_builder.extract_setting_from_text) -
    inaczej ta linia sama wygenerowalaby falszywe naruszenia.

    Zwraca (oczyszczony_tekst, wybrane_miejsce_lub_None, wynik_walidacji,
    ile_naprawek_wykonano).
    """
    from validator import validate_generated_text
    from prompt_builder import build_fix_prompt, extract_setting_from_text

    try:
        raw_text = generate_lesson_text(api_key, prompt, model_id=model_id, max_retries=2, retry_delay=10.0)
        used_model = model_id
    except Exception:
        raw_text = generate_lesson_text(api_key, prompt, model_id=fallback_model_id, max_retries=2, retry_delay=10.0)
        used_model = fallback_model_id

    cleaned_text, setting_name = extract_setting_from_text(raw_text)
    result = validate_generated_text(cleaned_text, language, known_lemmas, target_lemmas, min_target_occurrences)
    attempts_used = 0

    while not result["ok"] and attempts_used < max_repair_attempts:
        fix_prompt = build_fix_prompt(
            raw_text, result["violations"], result["missing_targets"], min_target_occurrences
        )
        raw_text = generate_lesson_text(api_key, fix_prompt, model_id=used_model, max_retries=2, retry_delay=10.0)
        cleaned_text, setting_name = extract_setting_from_text(raw_text)
        result = validate_generated_text(cleaned_text, language, known_lemmas, target_lemmas, min_target_occurrences)
        attempts_used += 1

    return cleaned_text, setting_name, result, attempts_used
