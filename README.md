# Silnik i+1 do nauki jezykow - Aplikacja Streamlit

Aplikacja webowa sluzaca do generowania spersonalizowanych, leksykalnie kontrolowanych lekcji jezykowych wedlug metody **i+1** (uzycie wylacznie slow znanych uzytkownikowi plus wyselekcjonowane nowe slowa z kolejnego pasma frekwencyjnego Zipf).

---

## Struktura projektu

```
jezyki-app/
├── app.py                      # Glowna aplikacja webowa Streamlit
├── freq_source.py              # Zrodla frekwencji slow (wordfreq, custom)
├── lemmatize.py                # Lematyzacja spaCy (de, it, es, en, fr)
├── coverage.py                 # Analiza pokrycia tekstu i dobor target words
├── validator.py                # Walidator twardych ograniczen leksykalnych
├── prompt_builder.py           # Generator promptow i+1 dla modeli LLM
├── registry.py                 # Rejestr SQLite (baza lekcji i pokrycia)
├── lingq_lesson_scan.py        # Pobieranie slow ze statusem "known" z LingQ
├── themes_de.json / _it / ...  # Tematyka dopasowana do zainteresowan
├── known_words_de.json / ...   # Baza znanych form powierzchniowych
├── requirements.txt            # Zaleznosci Python + modele spaCy (.whl)
├── .gitignore                  # Pliki ignorowane przez Git
└── .streamlit/
    └── secrets.toml.example    # Wzorzec konfiguracji sekretow
```

---

## Uruchomienie lokalne

1. **Instalacja zaleznosci:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Uruchomienie aplikacji:**
   ```powershell
   streamlit run app.py
   ```

3. **Lokalne sekrety (opcjonalnie):**
   Utworz plik `.streamlit/secrets.toml` na podstawie `.streamlit/secrets.toml.example` i wpisz swoj klucz LingQ:
   ```toml
   LINGQ_API_KEY = "twoj_klucz_api_lingq"
   ```

---

## Wdrozenie na Streamlit Community Cloud

1. **Utworz repozytorium na GitHubie:**
   - Utworz nowe repozytorium (np. `jezyki-app`) na swoim koncie GitHub (moze byc prywatne lub publiczne).
   - Wrzuc zawartosc tego folderu do repozytorium:
     ```powershell
     git init
     git add .
     git commit -m "Initial commit - Silnik i+1 Streamlit"
     git branch -M main
     git remote add origin https://github.com/TWOJ_LOGIN/jezyki-app.git
     git push -u origin main
     ```

2. **Podlacz repozytorium na Streamlit Cloud:**
   - Zaloguj sie na [share.streamlit.io](https://share.streamlit.io/).
   - Kliknij **"New app"**.
   - Wybierz swoje repozytorium, branch `main` oraz plik glowny `app.py`.

3. **Ustaw sekrety (Secrets) w panelu aplikacji:**
   - W ustawieniach wdrozonej aplikacji przejdz do **Settings** -> **Secrets**.
   - Wklej konfiguracje:
     ```toml
     LINGQ_API_KEY = "twoj_klucz_api_lingq"
     ```
   - Kliknij **Save**. Aplikacja zostanie automatycznie zrestartowana z dostepem do Twojego konta LingQ.

---

## Informacja o trwalosci danych

Streamlit Community Cloud operuje na efemerycznym systemie plikow (restart kontenera po bezczynnosci lub aktualizacji repozytorium przywraca stan z GitHuba).

W aplikacji w zakladce **"Przeglad slownictwa i eksport"** dostepne sa przyciski szybkiego pobrania zaktualizowanych baz `known_words_<lang>.json` oraz `jezyki_<lang>.db`, dzieki czemu w kazdej chwili mozesz zapisac kopie zapasowa na swoim komputerze lub zaktualizowac pliki w repozytorium.
