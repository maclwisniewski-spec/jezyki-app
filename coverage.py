"""
coverage.py

1. text_coverage - jaki procent tekstu pokrywa lista known_words (prog 95%
   = komfortowe czytanie, 98% = bez slownika, wg Nation 2006).
2. pick_next_unknown_words - idzie po rankingu czestotliwosci od gory,
   zwraca pierwsze N slow, ktorych uzytkownik jeszcze NIE zna. To jest
   glowny mechanizm wyboru "target words" do kazdej kolejnej lekcji.
3. estimate_vocab_size - probkowanie po pasmach Zipf + ekstrapolacja.
"""
from __future__ import annotations
import random
from collections import Counter
from freq_source import FrequencySource

ZIPF_BANDS = [(7, 6), (6, 5), (5, 4), (4, 3), (3, 2)]


def text_coverage(lemmas: list[str], known_lemmas: set[str]) -> dict:
    total_tokens = len(lemmas)
    if total_tokens == 0:
        return {"token_coverage": 0.0, "type_coverage": 0.0, "unknown_lemmas": [], "sample_size": 0}
    known_tokens = sum(1 for l in lemmas if l in known_lemmas)
    unique = set(lemmas)
    known_types = sum(1 for l in unique if l in known_lemmas)
    unknown = sorted(unique - known_lemmas)
    return {
        "token_coverage": round(100 * known_tokens / total_tokens, 2),
        "type_coverage": round(100 * known_types / len(unique), 2) if unique else 0.0,
        "unknown_lemmas": unknown,
        "sample_size": total_tokens,
    }


def sample_zipf_band(source: FrequencySource, low: float, high: float,
                      scan_limit: int = 10000, n: int = 10) -> list[str]:
    candidates = [
        w for w in source.ranked_words(scan_limit)
        if low <= source.zipf(w) < high and w.isalpha() and len(w) > 1
    ]
    return random.sample(candidates, min(n, len(candidates)))


def build_vocab_size_quiz(source: FrequencySource, n_per_band: int = 10) -> dict[str, list[str]]:
    return {
        f"{high}-{low}": sample_zipf_band(source, low, high, n=n_per_band)
        for high, low in ZIPF_BANDS
    }


def estimate_vocab_size(source: FrequencySource, quiz_results: dict[str, list[bool]]) -> int:
    band_sizes = _band_sizes(source)
    total = 0.0
    for band, results in quiz_results.items():
        if not results:
            continue
        known_pct = sum(results) / len(results)
        total += known_pct * band_sizes.get(band, 0)
    return round(total)


def _band_sizes(source: FrequencySource, scan_limit: int = 40000) -> dict[str, int]:
    counts = Counter()
    for w in source.ranked_words(scan_limit):
        if not (w.isalpha() and len(w) > 1):
            continue
        z = source.zipf(w)
        for high, low in ZIPF_BANDS:
            if low <= z < high:
                counts[f"{high}-{low}"] += 1
                break
    return dict(counts)


def pick_next_unknown_words(
    source: FrequencySource,
    known_lemmas: set[str],
    language: str,
    n: int = 8,
    scan_limit: int = 20000,
) -> list[str]:
    """Zwraca pierwsze n NIEZNANYCH slow, idac od najczestszych w dol rankingu."""
    from lemmatize import lemmatize_words_batch

    candidates = [w for w in source.ranked_words(scan_limit) if w.isalpha() and len(w) > 1]
    lemma_map = lemmatize_words_batch(candidates, language)

    found: list[str] = []
    seen: set[str] = set()
    for w in candidates:
        lemma = lemma_map[w]
        if lemma in known_lemmas or lemma in seen:
            continue
        seen.add(lemma)
        found.append(lemma)
        if len(found) >= n:
            break
    return found
