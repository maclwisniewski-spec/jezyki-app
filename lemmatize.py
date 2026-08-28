"""
lemmatize.py

Bez tego cala lista known_words to fikcja: "gehe / ging / gegangen" to
jedno slowo (jeden lemat), nie trzy rozne wpisy.
"""
from __future__ import annotations

SPACY_MODELS = {
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "en": "en_core_web_sm",
}

_nlp_cache: dict[str, object] = {}

FUNCTOR_POS = {"DET", "ADP", "CCONJ", "SCONJ", "PRON", "AUX", "PART"}


def _get_nlp(language: str):
    if language not in _nlp_cache:
        import spacy
        model = SPACY_MODELS.get(language)
        if model is None:
            raise ValueError(f"Brak skonfigurowanego modelu spaCy dla jezyka: {language}")
        try:
            _nlp_cache[language] = spacy.load(model)
        except OSError as exc:
            raise RuntimeError(
                f"Model spaCy '{model}' nie jest zainstalowany. "
                f"Uruchom: python -m spacy download {model}"
            ) from exc
    return _nlp_cache[language]


def lemmatize(text: str, language: str, drop_functors: bool = False) -> list[str]:
    nlp = _get_nlp(language)
    doc = nlp(text)
    out = []
    for tok in doc:
        if tok.is_punct or tok.is_space:
            continue
        if drop_functors and tok.pos_ in FUNCTOR_POS:
            continue
        out.append(tok.lemma_.lower())
    return out


def lemmatize_with_pos(text: str, language: str) -> list[tuple[str, str]]:
    nlp = _get_nlp(language)
    doc = nlp(text)
    return [
        (tok.lemma_.lower(), tok.pos_)
        for tok in doc if not tok.is_punct and not tok.is_space
    ]


def lemmatize_words_batch(words: list[str], language: str) -> dict[str, str]:
    """Lematyzuje liste pojedynczych slow naraz (nlp.pipe) - szybsze w petli."""
    nlp = _get_nlp(language)
    out: dict[str, str] = {}
    for word, doc in zip(words, nlp.pipe(words, batch_size=256)):
        tokens = [t for t in doc if not t.is_punct and not t.is_space]
        out[word] = tokens[0].lemma_.lower() if tokens else word.lower()
    return out
