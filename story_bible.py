"""
story_bible.py

"Biblia" powtarzalnej fabuly: stali bohaterowie + gatunek (thriller w stylu
Dana Browna - zagadka/spisek osadzony w prawdziwych miejscach). Miejsce
akcji NIE jest z gory ustalone - model sam wybiera dowolne prawdziwe
miasto/miasteczko/wioske/zabytek z tysiecy mozliwosci, w ramach kraju/ow
wlasciwych dla danego jezyka (patrz COUNTRY_HINTS), unikajac miejsc juz
odwiedzonych w poprzednich odcinkach.

Uzycie: import w prompt_builder.py (patrz build_thriller_prompt).
"""

CHARACTERS = """Glowni bohaterowie (ci sami we WSZYSTKICH odcinkach, w kazdym jezyku):

MACIEK - aplikant sedziowski na calorocznym urlopie zdrowotnym. Pasjonat
historii, zwlaszcza wojskowej i regionalnej europejskiej. Zna kilka jezykow
i historie w miare dobrze, ale podejmuje decyzje ryzykowne i impulsywne -
to on zazwyczaj wciaga obu w klopoty, bo nie potrafi zostawic zagadki
nierozwiazanej.

DAMIAN - najlepszy przyjaciel Maćka. Kiedys sam byl impulsywny, dzis jest
statecznym mezem i ojcem rodziny - ale w podrozy budzi sie w nim dawna
odwaga. Jest odwazniejszy interpersonalnie niz Maciek (latwo zjednuje sobie
ludzi, wyciaga informacje z nieznajomych) i wyraznie silniejszy fizycznie -
to on wyciaga ich z fizycznych opresji."""

GENRE_INSTRUCTIONS = """Gatunek: thriller/zagadka historyczna w stylu Dana Browna (jak "Kod
Leonarda da Vinci"). Kazdy odcinek to fragment wiekszej intrygi zwiazanej
z prawdziwym miejscem - Maciek i Damian odkrywaja trop prowadzacy do
kolejnego miejsca w nastepnym odcinku.

WYBOR MIEJSCA AKCJI:
- Wybierz SAM dowolne prawdziwe, istniejace miejsce - miasto, miasteczko,
  wioske, zamek, kosciol, ruiny, muzeum, most, cokolwiek realnego. Nie
  musi to byc najbardziej oczywisty zabytek - im ciekawsze i mniej
  banalne, tym lepiej.
- Wpleć naturalnie 2-3 fakty o tym miejscu, ktorych jestes NAPRAWDE
  pewien (data, tworca, wydarzenie historyczne). Jesli nie jestes pewien
  konkretnego szczegolu, nie zmyslaj go - opisz miejsce ogolniej zamiast
  podawac niepewna date czy nazwisko.
- Na sam koniec calej odpowiedzi dodaj linie w DOKLADNIE tym formacie
  (potrzebne do automatycznego zapisu, nie pomijaj tego):
  MIEJSCE_AKCJI: <nazwa miejsca, miasto, kraj>

WYMOGI OGOLNE:
- Trzymaj w napieciu: cliffhanger, poczucie zagrozenia lub pilnosci, ale
  bez przemocy graficznej.
- Zakoncz fabule w momencie naturalnie prowadzacym do kolejnego odcinka
  (odkryta wskazowka, ucieczka, telefon z nowa informacja, itp.)."""

# Ramy geograficzne per jezyk - model wybiera konkretne miejsce SAM w
# obrebie tego zakresu, nie z listy.
COUNTRY_HINTS = {
    "de": "kraje niemieckojezyczne (Niemcy, Austria, Szwajcaria, Liechtenstein)",
    "it": "Wlochy - dowolny region, od duzych miast po male miasteczka i wioski",
    "es": "Hiszpania lub kraje hiszpanskojezyczne Ameryki Lacinskiej (zwlaszcza Argentyna)",
    "en": "kraje anglojezyczne (Wielka Brytania, Irlandia, USA, Kanada, itd.)",
    "fr": "Francja - dowolny region, od Paryza po male miasteczka",
}
