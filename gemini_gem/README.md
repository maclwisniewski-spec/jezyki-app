# Silnik i+1 jako Gemini Gem (bez API, reczne wklejanie listy)

Najprostszy wariant: appka (ta ktora juz masz na Streamlit Cloud) generuje
liste slow, Ty ja kopiujesz/pobierasz, wklejasz do Gema razem z komenda
"wygeneruj". Zero hostingu, zero kluczy API w Gemini, dziala od razu.

## Krok 1: Wygeneruj liste w aplikacji

1. Wejdz do swojej appki, zakladka "📊 Przeglad slownictwa i eksport"
2. Wybierz jezyk w panelu bocznym (tak jak zawsze)
3. Ustaw suwak "Ile nowych slow do wprowadzenia" (domyslnie 40)
4. Kliknij "🔄 Przygotuj liste dla Gemini"
5. Skopiuj tekst z pola (ikonka kopiowania w prawym gornym rogu bloku)
   albo pobierz jako plik .txt

## Krok 2: Stworz Gema (raz, potem juz gotowe)

1. gemini.google.com -> Explore Gems -> New Gem
2. Nazwa: np. "Silnik i+1"
3. Instructions: wklej cala tresc pliku `GEM_INSTRUCTIONS.txt`
4. Save

## Krok 3: Uzywanie (za kazdym razem)

1. Otworz swojego Gema
2. Wklej cala liste slow skopiowana z appki
3. Napisz "wygeneruj" (albo "wygeneruj historyjke o [temat]", jesli
   chcesz konkretny temat)

Gdy chcesz nowa lekcje z nowym zestawem slow (np. po tygodniu czytania na
LingQ) - wroc do appki, kliknij "Przygotuj liste dla Gemini" jeszcze raz
(dane zawsze aktualne wg tego co masz w known_words_<jezyk>.json), i
wklej nowa liste do tej samej rozmowy z Gemem.

## Roznica wobec folderu gpt_api/

`gpt_api/` to pelna automatyzacja przez ChatGPT Custom GPT Actions (model
sam pobiera dane z LingQ) - wymaga osobnego hostingu API i ma ograniczenia
czasowe. To rozwiazanie (gemini_gem/) nie wymaga niczego wiecej niz to co
juz masz wdrozone - jest mniej "magiczne", ale prostsze i bez ryzyka
timeoutow.
