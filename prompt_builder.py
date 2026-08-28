"""
prompt_builder.py

Buduje prompt i+1: uzyj WYLACZNIE known_words, plus dokladnie N slow z
nastepnego pasma frekwencyjnego (target_words), kazde min. K razy.
Wspiera temat/tlo fabularne oraz kontynuacje poprzedniej historii.
"""
from __future__ import annotations

LANGUAGE_NAMES = {
    "de": "niemiecki",
    "fr": "francuski",
    "es": "hiszpanski",
    "it": "wloski",
    "en": "angielski",
}


def build_gap_prompt(
    known_lemmas: list[str],
    target_lemmas: list[str],
    language: str,
    min_target_occurrences: int = 2,
    text_type: str = "krotkie opowiadanie",
    length_hint: str = "150-250 slow",
    topic: str | None = None,
    previous_context: str | None = None,
) -> str:
    known_str = ", ".join(sorted(known_lemmas))
    target_str = ", ".join(target_lemmas)
    lang_name = LANGUAGE_NAMES.get(language, language)

    topic_line = f"- Temat/tlo fabularne: {topic}\n" if topic else ""
    continuity_block = (
        f"\nKONTYNUACJA: to jest kolejny odcinek tej samej historii. "
        f"Ostatnio skonczylo sie na:\n\"{previous_context}\"\n"
        f"Zacznij naturalnie od tego miejsca (nie powtarzaj tych zdan).\n"
        if previous_context else ""
    )

    return f"""Napisz {text_type} w jezyku: {lang_name}.
{topic_line}{continuity_block}
TWARDE OGRANICZENIE LEKSYKALNE (nieprzestrzeganie = tekst odrzucony):
- Uzywaj WYLACZNIE slow z tej listy (w dowolnej odmianie gramatycznej): {known_str}
- Rodzajniki, zaimki, spojniki i przyimki podstawowe mozesz uzywac swobodnie,
  nawet jesli nie sa explicite na liscie.
- Dodatkowo MUSISZ uzyc kazdego z tych {len(target_lemmas)} slow co najmniej
  {min_target_occurrences} razy, w roznych kontekstach zdaniowych: {target_str}
- Nie wprowadzaj zadnego innego slowa tresciowego spoza obu list.
- Dlugosc: {length_hint}.

Po tekscie dodaj sekcje "TARGET WORDS USED" z lista target words i liczba
wystapien kazdego - to zostanie zweryfikowane skryptem, wiec podaj rzetelnie.
"""
