"""
validator.py

Weryfikuj skryptem, nie zaufaniem: modele nie trzymaja ograniczen
leksykalnych w 100%. Sprawdza wygenerowany tekst wobec known_words +
target_words (min. N wystapien kazdego target worda).
"""
from __future__ import annotations
from collections import Counter
from lemmatize import lemmatize_with_pos, FUNCTOR_POS


def validate_generated_text(
    text: str,
    language: str,
    allowed_lemmas: set[str],
    target_lemmas: list[str],
    min_target_occurrences: int = 2,
    functors_exempt: bool = True,
    propn_exempt: bool = True,
) -> dict:
    allowed = allowed_lemmas | set(target_lemmas)
    tagged = lemmatize_with_pos(text, language)

    lemma_counts = Counter()
    violations = Counter()

    for lemma, pos in tagged:
        lemma_counts[lemma] += 1
        is_functor = functors_exempt and pos in FUNCTOR_POS
        # Nazwy wlasne (bohaterowie, miejsca akcji) nie sa "slownictwem do
        # nauki" - zawsze beda sie pojawiac, bez wzgledu na known_words.
        is_propn = propn_exempt and pos == "PROPN"
        if lemma not in allowed and not is_functor and not is_propn:
            violations[lemma] += 1

    target_coverage = {t: lemma_counts.get(t, 0) for t in target_lemmas}
    missing_targets = [t for t, c in target_coverage.items() if c < min_target_occurrences]

    return {
        "ok": not violations and not missing_targets,
        "violations": dict(violations),
        "target_coverage": target_coverage,
        "missing_targets": missing_targets,
    }
