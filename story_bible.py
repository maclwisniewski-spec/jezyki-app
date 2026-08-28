"""
story_bible.py

"Biblia" powtarzalnej fabuly: stali bohaterowie + gatunek (thriller w stylu
Dana Browna - zagadka/spisek osadzony w prawdziwych, konkretnych zabytkach)
+ lista realnych miejsc per jezyk, kazde z kilkoma sprawdzalnymi faktami,
zeby model mial gotowa, poprawna faktografie zamiast zmyslac szczegoly.

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
z prawdziwym zabytkiem/miejscem - Maciek i Damian odkrywaja trop
prowadzacy do kolejnego miejsca w nastepnym odcinku.

WYMOGI:
- Uzyj PRAWDZIWEGO miejsca wskazanego w "Miejsce akcji" i wpleć naturalnie
  faktografie podana ponizej (data, architekt/tworca, wydarzenie
  historyczne) - fikcyjna jest INTRYGA, nie samo miejsce i jego historia.
- Trzymaj w napieciu: cliffhanger, poczucie zagrozenia lub pilnosci, ale
  bez przemocy graficznej.
- Zakoncz w momencie naturalnie prowadzacym do kolejnego odcinka (odkryta
  wskazowka, ucieczka, telefon z nowa informacja, itp.)."""

# Kazde miejsce: nazwa + 2-3 sprawdzalne fakty, zeby model nie zmyslal
# szczegolow historycznych. Rotuja losowo miedzy odcinkami (patrz
# prompt_builder.pick_setting).
SETTINGS = {
    "de": [
        {"miejsce": "Reichstag w Berlinie",
         "fakty": ["budynek ukonczony w 1894 roku", "szklana kopula z 1999 roku, projekt Normana Fostera",
                    "siedziba niemieckiego Bundestagu"]},
        {"miejsce": "Brama Brandenburska w Berlinie",
         "fakty": ["ukonczona w 1791 roku", "przez dekady stala tuz przy Murze Berlinskim",
                    "wzorowana na Propylejach ateńskich"]},
        {"miejsce": "East Side Gallery - pozostalosci Muru Berlinskiego",
         "fakty": ["najdluzszy zachowany fragment muru, ok. 1.3 km",
                    "pomalowany przez artystow z calego swiata w 1990 roku"]},
        {"miejsce": "Palac Schönbrunn w Wiedniu",
         "fakty": ["letnia rezydencja Habsburgow", "1441 pokoi", "ogrody w stylu francuskim z XVIII wieku"]},
        {"miejsce": "Hofburg w Wiedniu",
         "fakty": ["przez wieki siedziba wladzy Habsburgow", "mieści Skarbiec Cesarski z insygniami koronacyjnymi"]},
        {"miejsce": "Festung Hohensalzburg w Salzburgu",
         "fakty": ["jedna z najwiekszych zachowanych twierdz sredniowiecznych w Europie",
                    "budowa rozpoczeta w 1077 roku"]},
        {"miejsce": "Katedra Grossmünster w Zurychu",
         "fakty": ["romanska katedra z XI-XIII wieku", "miejsce dzialalnosci reformatora Ulricha Zwingliego"]},
    ],
    "it": [
        {"miejsce": "Koloseum w Rzymie",
         "fakty": ["ukonczone w 80 roku n.e. za cesarza Tytusa", "miescilo do ok. 50-80 tysiecy widzow"]},
        {"miejsce": "Watykan i Kaplica Sykstynska",
         "fakty": ["sufit malowany przez Michala Aniola w latach 1508-1512",
                    "miejsce konklawe wybierajacego papieza"]},
        {"miejsce": "Katedra Santa Maria del Fiore we Florencji",
         "fakty": ["kopula Brunelleschiego ukonczona w 1436 roku, najwieksza murowana kopula na swiecie w tamtym czasie"]},
        {"miejsce": "Bazylika sw. Marka w Wenecji",
         "fakty": ["budowa rozpoczeta w XI wieku", "mozaiki pokrywaja ponad 8000 m2"]},
        {"miejsce": "Wykopaliska w Pompejach",
         "fakty": ["miasto zasypane popiolem podczas erupcji Wezuwiusza w 79 roku n.e.",
                    "odkryte na nowo systematycznie od XVIII wieku"]},
        {"miejsce": "Castel dell'Ovo w Neapolu",
         "fakty": ["najstarszy zamek w Neapolu", "wedlug legendy w fundamentach ukryte jajko chroniace miasto"]},
        {"miejsce": "Antyczny teatr grecki w Syrakuzach",
         "fakty": ["jeden z najwiekszych zachowanych teatrow greckich", "wykuty w skale w V wieku p.n.e."]},
    ],
    "es": [
        {"miejsce": "Palacio Real w Madrycie",
         "fakty": ["oficjalna rezydencja krolow Hiszpanii (uzywana ceremonialnie)", "ponad 3400 pomieszczen"]},
        {"miejsce": "Katedra i dzielnice trzech kultur w Toledo",
         "fakty": ["miasto bylo przez wieki miejscem wspolistnienia chrzescijan, zydow i muzulmanow",
                    "katedra budowana od 1226 do 1493 roku"]},
        {"miejsce": "Sagrada Familia w Barcelonie",
         "fakty": ["projekt Antoniego Gaudiego rozpoczety w 1882 roku", "wciaz nieukonczona"]},
        {"miejsce": "Alhambra w Grenadzie",
         "fakty": ["palac i twierdza dynastii Nasrydow", "przyklad architektury mauretanskiej z XIII-XIV wieku"]},
        {"miejsce": "Casa Rosada i Plaza de Mayo w Buenos Aires",
         "fakty": ["siedziba prezydenta Argentyny", "miejsce historycznych wystapien Evity Peron"]},
        {"miejsce": "Cmentarz Recoleta w Buenos Aires",
         "fakty": ["miejsce pochowku Evity Peron", "monumentalne mauzolea najbogatszych rodzin Argentyny"]},
        {"miejsce": "Jezuickie estancje kolo Cordoby (Argentyna)",
         "fakty": ["zalozone przez jezuitow w XVII wieku", "wpisane na liste UNESCO"]},
    ],
    "en": [
        {"miejsce": "Tower of London",
         "fakty": ["budowa rozpoczeta przez Wilhelma Zdobywce ok. 1078 roku", "przechowuje Klejnoty Koronne"]},
        {"miejsce": "Westminster Abbey w Londynie",
         "fakty": ["miejsce koronacji brytyjskich monarchow od 1066 roku"]},
        {"miejsce": "Edinburgh Castle",
         "fakty": ["stoi na wygasłym wulkanie", "jedna z najczesciej atakowanych twierdz w historii Wielkiej Brytanii"]},
        {"miejsce": "Trinity College i Book of Kells w Dublinie",
         "fakty": ["Book of Kells to iluminowany manuskrypt z ok. 800 roku n.e."]},
        {"miejsce": "Bodleian Library w Oksfordzie",
         "fakty": ["jedna z najstarszych bibliotek w Europie, otwarta w 1602 roku"]},
    ],
    "fr": [
        {"miejsce": "Katedra Notre-Dame w Paryzu",
         "fakty": ["budowa rozpoczeta w 1163 roku", "powazny pozar w 2019 roku, trwa odbudowa"]},
        {"miejsce": "Luwr w Paryzu",
         "fakty": ["dawniej twierdza i palac krolewski", "najczesciej odwiedzane muzeum na swiecie"]},
        {"miejsce": "Palac Wersalski",
         "fakty": ["rezydencja Ludwika XIV", "Sala Lustrzana - miejsce podpisania traktatu wersalskiego w 1919"]},
        {"miejsce": "Twierdza Carcassonne",
         "fakty": ["sredniowieczne miasto-twierdza z podwojnym pierscieniem murow"]},
    ],
}
