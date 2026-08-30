# Silnik i+1 w ChatGPT (Custom GPT + Actions)

## Jak to dziala

1. Ty piszesz w ChatGPT: "generuj historyjke z dialogami" (po niemiecku/wlosku/itd.)
2. Custom GPT wywoluje akcje `getVocab` -> mala apka (ten folder) pobiera z
   LingQ Twoje known words + slowa "w trakcie nauki", i zwraca liste
   kolejnych NIEZNANYCH slow posortowana wg popularnosci (wordfreq)
3. ChatGPT sam pisze historyjke (500-800 slow, dialogi), pilnujac zeby
   min. 20% tekstu to byly te nowe slowa
4. Custom GPT wywoluje akcje `checkCoverage`, zeby to zweryfikowac; jesli
   za malo nowych slow - poprawia i sprawdza ponownie

## Krok 1: Wdroz API (Render.com - darmowe, logowanie przez GitHub)

1. Wejdz na render.com, zaloguj sie przez GitHub (to samo konto co
   `jezyki-app`)
2. New -> Web Service -> polacz repo `jezyki-app`
3. Ustawienia:
   - **Root Directory**: zostaw puste (root repo)
   - **Build Command**: `pip install -r gpt_api/requirements.txt`
   - **Start Command**: `uvicorn gpt_api.api:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. W sekcji Environment dodaj zmienne:
   - `LINGQ_API_KEY` = Twoj klucz z lingq.com/en/accounts/apikey/
   - `SERVICE_API_KEY` = wymysl dowolny dlugi losowy string (np. z
     generatora hasel) - to sekret chroniacy Twoje API przed obcymi
   - `PREWARM_LANGUAGES` = `de,it,es,en` (albo ktore jezyki uzywasz)
5. Deploy. Po zakonczeniu budowania dostaniesz URL w stylu
   `https://jezyki-app-xxxx.onrender.com`

**WAZNE - darmowy tier Render usypia po 15 min bezczynnosci.** Pierwsze
zapytanie po przerwie obudzi serwer (10-30s) I ZACZNIE skan LingQ (kolejne
40-70s) - to razem moze przekroczyc czas jaki ChatGPT czeka na akcje.
Jesli pierwsza probka historyjki zwroci blad/timeout w ChatGPT, po prostu
napisz "sprobuj jeszcze raz" po 30-60 sekundach - serwer w tym czasie
dokonczy prace w tle, a druga proba bedzie juz szybka (cache).

## Krok 2: Sprawdz, ze API dziala

Otworz w przegladarce: `https://TWOJ-URL.onrender.com/health` - powinienes
zobaczyc `{"status":"ok","lingq_key_configured":true,"service_key_configured":true}`.

## Krok 3: Stworz Custom GPT w ChatGPT

1. W ChatGPT: Explore GPTs -> Create (potrzebny ChatGPT Plus)
2. Zakladka "Configure":
   - Name: np. "Silnik i+1"
   - Instructions: wklej cala tresc pliku `GPT_INSTRUCTIONS.txt`
3. Sekcja "Actions" -> Create new action:
   - Kliknij "Import from URL" i wpisz: `https://TWOJ-URL.onrender.com/openapi.json`
     (FastAPI generuje schemat automatycznie - nic nie trzeba pisac recznie)
   - Authentication: wybierz "API Key", Auth Type: "Custom", Header name:
     `X-API-Key`, wartosc: to samo co ustawiles jako `SERVICE_API_KEY` w
     Render
4. Zapisz GPT (Save -> Only me, chyba ze chcesz go udostepnic)

## Krok 4: Przetestuj

Napisz w GPT: "generuj historyjke z dialogami po niemiecku". Pierwsza
proba (jesli serwer spal) moze nie wypalic - patrz uwaga w Kroku 1.

## Pliki w tym folderze

- `api.py` - serwer FastAPI (getVocab, checkCoverage, refresh, health)
- `requirements.txt` - zaleznosci do zainstalowania na Render
- `GPT_INSTRUCTIONS.txt` - gotowa tresc do wklejenia w konfiguracji GPT
