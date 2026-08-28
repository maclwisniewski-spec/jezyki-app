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


def build_thriller_prompt(
    known_lemmas: list[str],
    target_lemmas: list[str],
    language: str,
    in_progress_lemmas: list[str] | None = None,
    min_target_occurrences: int = 2,
    length_hint: str = "500-800 slow",
    used_settings: list[str] | None = None,
    previous_context: str | None = None,
) -> str:
    """
    Wersja build_gap_prompt osadzona w powtarzalnej fabule (Maciek + Damian,
    thriller w stylu Dana Browna). Miejsce akcji NIE jest z gory ustalone -
    model sam wybiera dowolne prawdziwe miejsce w ramach kraju/ow
    wlasciwych dla danego jezyka, unikajac used_settings (poprzednio
    odwiedzonych miejsc z historii). Trzy poziomy slownictwa: known
    (swobodnie), in_progress (gdzieniegdzie, bez wymogu powtorzen), target
    (nowe, min. N powtorzen kazde).
    """
    from story_bible import CHARACTERS, GENRE_INSTRUCTIONS, COUNTRY_HINTS

    known_str = ", ".join(sorted(known_lemmas))
    target_str = ", ".join(target_lemmas)
    in_progress_lemmas = in_progress_lemmas or []
    in_progress_str = ", ".join(in_progress_lemmas)
    lang_name = LANGUAGE_NAMES.get(language, language)
    country_hint = COUNTRY_HINTS.get(language, "")

    geography_block = f"\nZasieg geograficzny: {country_hint}.\n" if country_hint else ""
    used_settings = used_settings or []
    avoid_block = (
        f"Miejsca juz odwiedzone w poprzednich odcinkach (WYBIERZ COS INNEGO): "
        f"{'; '.join(used_settings)}\n"
        if used_settings else ""
    )

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
{geography_block}{avoid_block}{continuity_block}
FORMA: proza narracyjna (jak w powiesci), NIE scenariusz filmowy. Zero
didaskaliow, opisow scen typu "INT./EXT.", nazw scen, ani imion pisanych
WIELKIMI LITERAMI przed kwestiami dialogowymi - dialogi wplataj naturalnie
w tekst narracyjny (np. Damian powiedzial: "...").

TWARDE OGRANICZENIE LEKSYKALNE (nieprzestrzeganie = tekst odrzucony):
- Uzywaj WYLACZNIE slow z tej listy (w dowolnej odmianie gramatycznej): {known_str}
- Rodzajniki, zaimki, spojniki i przyimki podstawowe mozesz uzywac swobodnie.
- Dodatkowo MUSISZ uzyc kazdego z tych {len(target_lemmas)} NOWYCH slow co
  najmniej {min_target_occurrences} razy, w roznych kontekstach: {target_str}
{in_progress_block}- Nie wprowadzaj zadnego innego slowa tresciowego spoza tych list (nazwy
  wlasne - imiona bohaterow, nazwy miejsc - sa dozwolone bez ograniczen).
- Dlugosc: {length_hint}.

Po tekscie dodaj sekcje "TARGET WORDS USED" z lista nowych slow (nie
liczac slow "w trakcie nauki") i liczba wystapien kazdego. Pamietaj tez o
linii "MIEJSCE_AKCJI: ..." opisanej wyzej w instrukcjach gatunkowych.
"""


def extract_setting_from_text(text: str) -> tuple[str, str | None]:
    """
    Wyciaga linie 'MIEJSCE_AKCJI: ...' z konca wygenerowanego tekstu.
    Zwraca (tekst_bez_tej_linii, nazwa_miejsca_albo_None).
    """
    import re
    match = re.search(r"MIEJSCE_AKCJI:\s*(.+)", text)
    if not match:
        return text, None
    setting_name = match.group(1).strip()
    cleaned = text[:match.start()].rstrip()
    return cleaned, setting_name


def build_fix_prompt(previous_text: str, violations: dict[str, int], missing_targets: list[str],
                      min_target_occurrences: int = 2) -> str:
    """
    Buduje prompt naprawczy do wyslania modelowi, ktory nie utrzymal
    ograniczen leksykalnych za pierwszym razem. Uzywany zarowno w petli
    automatycznej (gemini_client.generate_and_validate_lesson) jak i w
    UI do recznej poprawki w innym modelu.
    """
    parts = [
        "Twoj poprzedni tekst zawieral nastepujace naruszenia ograniczen leksykalnych:\n",
    ]
    if violations:
        parts.append(f"- Uzyto slow spoza dozwolonej listy: {list(violations.keys())}\n")
    if missing_targets:
        parts.append(
            f"- Zbyt malo wystapien wymaganych target words (min. {min_target_occurrences} kazde): {missing_targets}\n"
        )
    parts.append(
        "\nPrzepisz CALY tekst od nowa, zachowujac te sama fabule, bohaterow i "
        "miejsce akcji, ale usuwajac WSZYSTKIE powyzsze naruszenia - zastap "
        "kazde niedozwolone slowo synonimem z dozwolonej listy albo "
        "przeformuluj zdanie tak, zeby go uniknac. Pamietaj o wszystkich "
        "pierwotnych ograniczeniach (tylko known_words + target_words, "
        "min. wystapien kazdego target worda, proza a nie scenariusz). "
        "Jesli poprzedni tekst konczyl sie linia \"MIEJSCE_AKCJI: ...\", "
        "zachowaj ja BEZ ZMIAN na koncu nowej wersji.\n\n"
        f"Oto poprzedni tekst do poprawy:\n\n{previous_text}"
    )
    return "".join(parts)
