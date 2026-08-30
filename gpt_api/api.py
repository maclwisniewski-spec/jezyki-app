"""
api.py

Serwer FastAPI dla Custom GPT w ChatGPT (przez GPT Actions). Sam tekst
historii pisze model w ChatGPT - to API tylko dostarcza mu wlasciwe
listy slow: known + in_progress (z LingQ) oraz next_unknown_words
(kolejne nieznane slowa wg rankingu czestotliwosci wordfreq).

Endpointy:
  GET  /vocab?language=de          -> listy slow do zbudowania historii
  POST /refresh?language=de         -> wymusza odswiezenie z LingQ w tle
  POST /check_coverage              -> sprawdza % nowych slow w gotowym tekscie
  GET  /health                      -> healthcheck

WAZNE O WYDAJNOSCI: pelny skan LingQ (wszystkie lekcje) trwa 40-70 sekund
- to prawdopodobnie WIECEJ niz limit czasu na pojedyncze wywolanie Action
w ChatGPT. Dlatego /vocab dziala w trybie "stale-while-revalidate":
zwraca NATYCHMIAST to co ma w cache (nawet jesli nieco nieaktualne), i w
tle odswieza dane na nastepne zapytanie. Przy pierwszym uzyciu w ogole
(caly cache pusty) i tak trzeba poczekac na pelny skan - patrz sekcja
"Rozgrzewka" nizej.

Rozgrzewka: przy starcie serwera automatycznie odpala sie skan dla
jezykow z PREWARM_LANGUAGES (np. "de,it,es,en") w tle, zeby cache byl
gotowy zanim faktycznie zaczniesz rozmowe w ChatGPT.

Autoryzacja: naglowek X-API-Key musi zgadzac sie z SERVICE_API_KEY (zmienna
srodowiskowa) - to chroni przed obcymi wywolaniami z internetu (kazde
zapytanie kosztuje czas i request-y do LingQ).

Zmienne srodowiskowe wymagane na serwerze:
  LINGQ_API_KEY      - Twoj klucz z lingq.com/en/accounts/apikey/
  SERVICE_API_KEY    - dowolny wymyslony sekret, ten sam co w konfiguracji
                       Action w ChatGPT (Authentication -> API Key)
  PREWARM_LANGUAGES  - opcjonalnie, np. "de,it,es,en" (domyslnie puste)
"""
from __future__ import annotations
import os
import threading
import time
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from freq_source import WordfreqSource
from lemmatize import lemmatize, lemmatize_words_batch
from lingq_lesson_scan import scan_known_words, get_in_progress_terms

app = FastAPI(
    title="Jezyki i+1 API",
    version="1.0",
    description="Dostarcza known/in-progress/next-unknown words z LingQ + wordfreq dla Custom GPT.",
)

LINGQ_API_KEY = os.environ.get("LINGQ_API_KEY", "")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "")
PREWARM_LANGUAGES = [l.strip() for l in os.environ.get("PREWARM_LANGUAGES", "").split(",") if l.strip()]

# Cache w pamieci: jezyk -> (timestamp, known_lemmas, inprogress_lemmas).
# "Stale-while-revalidate": zwracamy to co jest, odswiezamy w tle gdy stare.
_CACHE_FRESH_SECONDS = 3600  # ponizej tego wieku, nie odswiezaj wcale
_cache: dict[str, tuple[float, set[str], set[str]]] = {}
_refresh_locks: dict[str, threading.Lock] = {}


def _check_auth(x_api_key: Optional[str]) -> None:
    if not SERVICE_API_KEY:
        raise HTTPException(500, "Serwer nie ma skonfigurowanego SERVICE_API_KEY.")
    if x_api_key != SERVICE_API_KEY:
        raise HTTPException(401, "Nieprawidlowy lub brakujacy klucz API (naglowek X-API-Key).")


def _fetch_fresh_lemmas(language: str) -> tuple[set[str], set[str]]:
    """Pelny, synchroniczny skan LingQ (40-70s) - lematyzacja WSADOWA (szybka)."""
    known_words, _ = scan_known_words(LINGQ_API_KEY, language)
    inprogress_words = get_in_progress_terms(LINGQ_API_KEY, language)

    all_words = list(known_words | inprogress_words)
    lemma_map = lemmatize_words_batch(all_words, language)

    known_lemmas = {lemma_map[w] for w in known_words}
    inprogress_lemmas = {lemma_map[w] for w in inprogress_words}
    return known_lemmas, inprogress_lemmas


def _refresh_cache_blocking(language: str) -> None:
    lock = _refresh_locks.setdefault(language, threading.Lock())
    if not lock.acquire(blocking=False):
        return  # odswiezanie tego jezyka juz trwa w innym watku
    try:
        known_lemmas, inprogress_lemmas = _fetch_fresh_lemmas(language)
        _cache[language] = (time.time(), known_lemmas, inprogress_lemmas)
    finally:
        lock.release()


def _get_known_and_inprogress_lemmas(language: str, background_tasks: Optional[BackgroundTasks] = None
                                      ) -> tuple[set[str], set[str]]:
    if not LINGQ_API_KEY:
        raise HTTPException(500, "Brak skonfigurowanego LINGQ_API_KEY na serwerze.")

    cached = _cache.get(language)

    if cached is None:
        # Zupelnie pusty cache (pierwsze uzycie) - trzeba poczekac synchronicznie.
        _refresh_cache_blocking(language)
        cached = _cache[language]
        return cached[1], cached[2]

    age = time.time() - cached[0]
    if age > _CACHE_FRESH_SECONDS and background_tasks is not None:
        # Dane sa, ale stare - zwroc je od razu, odswiez w tle na nastepny raz.
        background_tasks.add_task(_refresh_cache_blocking, language)

    return cached[1], cached[2]


@app.on_event("startup")
def _prewarm() -> None:
    for lang in PREWARM_LANGUAGES:
        threading.Thread(target=_refresh_cache_blocking, args=(lang,), daemon=True).start()


class VocabResponse(BaseModel):
    language: str
    known_word_count: int
    in_progress_word_count: int
    next_unknown_words: list[str]
    instructions_for_model: str


@app.post("/refresh")
def refresh_vocab(
    background_tasks: BackgroundTasks,
    language: str = Query(..., description="Kod jezyka: de, it, es, en, fr"),
    x_api_key: Optional[str] = Header(None),
):
    """Wymusza odswiezenie cache w tle (nie czeka na wynik) - zawsze zwraca natychmiast."""
    _check_auth(x_api_key)
    background_tasks.add_task(_refresh_cache_blocking, language)
    already_cached = language in _cache
    return {
        "status": "odswiezanie rozpoczete w tle",
        "mial_juz_dane": already_cached,
        "message": (
            "Dane juz byly dostepne - zostana podmienione po zakonczeniu skanu."
            if already_cached
            else "To pierwsze uzycie dla tego jezyka - poczekaj 30-70 sekund i sprobuj /vocab ponownie."
        ),
    }


@app.get("/vocab", response_model=VocabResponse)
def get_vocab(
    background_tasks: BackgroundTasks,
    language: str = Query(..., description="Kod jezyka: de, it, es, en, fr"),
    n_new: int = Query(60, description="Ile kolejnych nieznanych slow zwrocic (posortowane od najpopularniejszych)"),
    x_api_key: Optional[str] = Header(None),
):
    _check_auth(x_api_key)
    known_lemmas, inprogress_lemmas = _get_known_and_inprogress_lemmas(language, background_tasks)
    exclude = known_lemmas | inprogress_lemmas

    src = WordfreqSource(language)
    candidates = [w for w in src.ranked_words(20000) if w.isalpha() and len(w) > 1]
    lemma_map = lemmatize_words_batch(candidates, language)

    next_unknown: list[str] = []
    seen: set[str] = set()
    for w in candidates:
        lemma = lemma_map[w]
        if lemma in exclude or lemma in seen:
            continue
        seen.add(lemma)
        next_unknown.append(lemma)
        if len(next_unknown) >= n_new:
            break

    return VocabResponse(
        language=language,
        known_word_count=len(known_lemmas),
        in_progress_word_count=len(inprogress_lemmas),
        next_unknown_words=next_unknown,
        instructions_for_model=(
            "next_unknown_words jest posortowana od najpopularniejszych (wg wordfreq) "
            "do mniej popularnych. Uzyj ich w tej kolejnosci - zaczynaj wprowadzanie "
            "nowego slownictwa od poczatku listy."
        ),
    )


class CoverageCheckRequest(BaseModel):
    language: str
    text: str


class CoverageCheckResponse(BaseModel):
    new_word_ratio: float
    target_met: bool
    new_words_used: list[str]
    message: str


@app.post("/check_coverage", response_model=CoverageCheckResponse)
def check_coverage(req: CoverageCheckRequest, x_api_key: Optional[str] = Header(None)):
    _check_auth(x_api_key)
    known_lemmas, inprogress_lemmas = _get_known_and_inprogress_lemmas(req.language)
    allowed_known = known_lemmas | inprogress_lemmas

    text_lemmas = lemmatize(req.text, req.language)
    if not text_lemmas:
        return CoverageCheckResponse(
            new_word_ratio=0.0, target_met=False, new_words_used=[],
            message="Pusty tekst - nie mozna policzyc pokrycia.",
        )

    new_words = [l for l in text_lemmas if l not in allowed_known]
    ratio = round(len(new_words) / len(text_lemmas), 3)
    target_met = ratio >= 0.20

    message = (
        f"OK: {ratio * 100:.1f}% tekstu to nowe slowa (cel: min. 20%)."
        if target_met
        else f"ZA MALO: tylko {ratio * 100:.1f}% tekstu to nowe slowa (cel: min. 20%). "
             f"Przepisz tekst, wprowadzajac wiecej slow z next_unknown_words."
    )

    return CoverageCheckResponse(
        new_word_ratio=ratio,
        target_met=target_met,
        new_words_used=sorted(set(new_words)),
        message=message,
    )


@app.get("/health")
def health():
    return {"status": "ok", "lingq_key_configured": bool(LINGQ_API_KEY), "service_key_configured": bool(SERVICE_API_KEY)}
