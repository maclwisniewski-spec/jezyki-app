"""
validator.py

Pedagogicznie uzasadniona weryfikacja i+1:
1. Zwalnia z ograniczen kategorie niebedace leksyka tresciowa:
   - Funktory (DET, ADP, CCONJ, SCONJ, PRON, AUX, PART)
   - Nazwy wlasne (PROPN - imiona bohaterow, miasta, zabytki)
   - Liczby i daty (NUM - np. 1894, zwei, dreihundert)
   - Symbole, skroty, wykrzykniki (SYM, X, INTJ)
2. Obsluguje warianty pisowni niemieckiej (ss <-> ß).
3. Oblicza rzeczywiste Token Coverage (% znanych slow).
   Wg standardu Nation (2006) i Krashena (i+1), pokrycie 95-98% to
   idealny poziom zrozumialego tekstu bez koniecznosci uzywania slownika.
4. Kryterium zaliczenia (ok):
   - Token coverage >= min_coverage_pct (domyslnie 95.0%)
   - Uzycie min. 50% target words (co najmniej 1 raz)
   - Brak dyskwalifikujacych brakow
"""
from __future__ import annotations
from collections import Counter
from lemmatize import lemmatize_with_pos

EXEMPT_POS = {
    "DET", "ADP", "CCONJ", "SCONJ", "PRON", "AUX", "PART",
    "NUM", "SYM", "X", "INTJ", "PUNCT", "SPACE", "PROPN"
}


def _normalize_variant(word: str) -> set[str]:
    """Generuje warianty zapisu dla danego slowa (np. niemieckie ss vs ß, umlauty ae/oe/ue vs ä/ö/ü)."""
    w = word.lower()
    variants = {w}
    if "ss" in w:
        variants.add(w.replace("ss", "ß"))
    if "ß" in w:
        variants.add(w.replace("ß", "ss"))
    if "ä" in w:
        variants.add(w.replace("ä", "ae"))
    if "ae" in w:
        variants.add(w.replace("ae", "ä"))
    if "ö" in w:
        variants.add(w.replace("ö", "oe"))
    if "oe" in w:
        variants.add(w.replace("oe", "ö"))
    if "ü" in w:
        variants.add(w.replace("ü", "ue"))
    if "ue" in w:
        variants.add(w.replace("ue", "ü"))
    return variants


def validate_generated_text(
    text: str,
    language: str,
    allowed_lemmas: set[str],
    target_lemmas: list[str],
    min_target_occurrences: int = 1,
    min_coverage_pct: float = 95.0,
    functors_exempt: bool = True,
    propn_exempt: bool = True,
    strict_zero_violations: bool = False,
) -> dict:
    """
    Waliduje wygenerowany tekst i oblicza metryki pokrycia i+1.
    """
    # Budujemy rozszerzony zbior dozwolonych lematow (z wariantami ss/ß)
    allowed_set = set()
    for l in (allowed_lemmas | set(target_lemmas)):
        allowed_set.update(_normalize_variant(l))

    tagged = lemmatize_with_pos(text, language)

    lemma_counts = Counter()
    violations = Counter()

    total_tokens = 0
    known_tokens = 0
    exempt_tokens = 0

    for lemma, pos in tagged:
        lemma_lower = lemma.lower()
        lemma_variants = _normalize_variant(lemma_lower)
        
        # Sprawdz czy slowo jest w target_lemmas (dla zliczania powtorzen)
        for t in target_lemmas:
            if t.lower() in lemma_variants:
                lemma_counts[t] += 1

        is_exempt = False
        if functors_exempt and pos in EXEMPT_POS:
            is_exempt = True
        elif propn_exempt and pos == "PROPN":
            is_exempt = True

        if is_exempt:
            exempt_tokens += 1
            continue

        total_tokens += 1
        # Sprawdz czy lemma jest w dozwolonych
        if any(v in allowed_set for v in lemma_variants):
            known_tokens += 1
        else:
            violations[lemma_lower] += 1

    # Obliczenie procentu pokrycia leksykalnego (Token Coverage dla slow tresciowych)
    token_coverage = round((known_tokens / total_tokens * 100), 1) if total_tokens > 0 else 100.0
    
    # Target words coverage
    target_coverage = {t: lemma_counts.get(t, 0) for t in target_lemmas}
    used_targets = [t for t, c in target_coverage.items() if c >= 1]
    missing_targets = [t for t, c in target_coverage.items() if c < min_target_occurrences]

    # Warunki akceptacji
    if strict_zero_violations:
        is_ok = (len(violations) == 0) and (len(missing_targets) == 0)
    else:
        # Standard i+1:
        # 1. Pokrycie leksykalne >= min_coverage_pct (domyslnie 95.0%)
        # 2. Co najmniej polowa target words uzyta min. 1 raz (lub 100% jesli targetow malo)
        target_threshold = max(1, len(target_lemmas) // 2) if target_lemmas else 0
        targets_ok = len(used_targets) >= target_threshold
        coverage_ok = token_coverage >= min_coverage_pct
        is_ok = coverage_ok and targets_ok

    return {
        "ok": is_ok,
        "token_coverage": token_coverage,
        "total_content_tokens": total_tokens,
        "known_content_tokens": known_tokens,
        "exempt_tokens": exempt_tokens,
        "violations": dict(violations),
        "target_coverage": target_coverage,
        "missing_targets": missing_targets,
        "used_targets_count": len(used_targets),
        "total_targets_count": len(target_lemmas),
    }
