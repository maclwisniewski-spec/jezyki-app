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


def pick_setting(language: str, exclude: str | None = None) -> dict | None:
    """Losuje jedno miejsce (z faktami) z story_bible.SETTINGS, unikajac ostatnio uzytego."""
    import random
    from story_bible import SETTINGS
    options = SETTINGS.get(language, [])
    if not options:
        return None
    candidates = [s for s in options if s["miejsce"] != exclude] or options
    return random.choice(candidates)


def build_thriller_prompt(
    known_lemmas: list[str],
    target_lemmas: list[str],
    language: str,
    in_progress_lemmas: list[str] | None = None,
    min_target_occurrences: int = 2,
    length_hint: str = "500-800 slow",
    setting: dict | None = None,
    previous_context: str | None = None,
) -> str:
    """
    Wersja build_gap_prompt osadzona w powtarzalnej fabule (Maciek + Damian,
    thriller w stylu Dana Browna, realne miejsca z faktami z story_bible.py).
    Trzy poziomy slownictwa: known (swobodnie), in_progress (gdzieniegdzie,
    bez wymogu powtorzen), target (nowe, min. N powtorzen kazde).
    """
    from story_bible import CHARACTERS, GENRE_INSTRUCTIONS

    if setting is None:
        setting = pick_setting(language)

    known_str = ", ".join(sorted(known_lemmas))
    target_str = ", ".join(target_lemmas)
    in_progress_lemmas = in_progress_lemmas or []
    in_progress_str = ", ".join(in_progress_lemmas)
    lang_name = LANGUAGE_NAMES.get(language, language)

    setting_block = ""
    if setting:
        fakty_str = "; ".join(setting["fakty"])
        setting_block = f"\nMiejsce akcji: {setting['miejsce']}\nFakty do wplecenia: {fakty_str}\n"

    continuity_block = (
        f"\nKONTYNUACJA: to kolejny odcinek tej samej historii. Ostatnio "
        f"skonczylo sie na:\n\"{previous_context}\"\n"
        f"Zacznij naturalnie od tego miejsca (nie powtarzaj tych zdan).\n"
        if previous_context
        else "\nTo PIERWSZY odcinek tej historii - przedstaw bohaterow i "
             "okolicznosci ich podrozy w sposob naturalny dla tego gatunku.\n"
    )

    in_progress_block = (
        f"- Tam gdzie to naturalne, wpleć TAKZE (bez wymogu liczby powtorzen) "
        f"te utrwalane ostatnio slowa: {in_progress_str}\n"
        if in_progress_str else ""
    )

    return f"""Napisz odcinek serialu w jezyku: {lang_name}.

{CHARACTERS}

{GENRE_INSTRUCTIONS}
{setting_block}{continuity_block}
TWARDE OGRANICZENIE LEKSYKALNE (nieprzestrzeganie = tekst odrzucony):
- Uzywaj WYLACZNIE slow z tej listy (w dowolnej odmianie gramatycznej): {known_str}
- Rodzajniki, zaimki, spojniki i przyimki podstawowe mozesz uzywac swobodnie.
- Dodatkowo MUSISZ uzyc kazdego z tych {len(target_lemmas)} NOWYCH slow co
  najmniej {min_target_occurrences} razy, w roznych kontekstach: {target_str}
{in_progress_block}- Nie wprowadzaj zadnego innego slowa tresciowego spoza tych list.
- Dlugosc: {length_hint}.

Po tekscie dodaj sekcje "TARGET WORDS USED" z lista nowych slow (nie
liczac slow "w trakcie nauki") i liczba wystapien kazdego.
"""
