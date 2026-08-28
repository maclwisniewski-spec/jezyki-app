"""
app.py

Aplikacja webowa Streamlit dla silnika i+1 do nauki jezykow.
Obsluguje generowanie spersonalizowanych lekcji, twarda walidacje
leksykalna, synchronizacje z LingQ oraz zarzadzanie historia.
"""
from __future__ import annotations
import io
import json
import os
import random
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Gwarancja dostepnosci modulow lokalnych na Streamlit Cloud
BASE_DIR = Path(__file__).parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st

from freq_source import WordfreqSource
from coverage import pick_next_unknown_words, text_coverage
from prompt_builder import build_gap_prompt, build_thriller_prompt, extract_setting_from_text, LANGUAGE_NAMES
from lemmatize import lemmatize
from validator import validate_generated_text
from registry import connect, save_text, log_coverage, get_recent_texts, get_used_settings
from lingq_lesson_scan import scan_known_words, get_in_progress_lemmas

st.set_page_config(
    page_title="Silnik i+1 - Nauka Jezykow",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

LANG_CONFIG = {
    "de": {"name": "Niemiecki", "flag": "🇩🇪"},
    "it": {"name": "Wloski", "flag": "🇮🇹"},
    "es": {"name": "Hiszpanski", "flag": "🇪🇸"},
    "en": {"name": "Angielski", "flag": "🇬🇧"},
    "fr": {"name": "Francuski", "flag": "🇫🇷"},
}

BASE_DIR = Path(__file__).parent.resolve()


# ==============================================================================
# Helpery danych i cache
# ==============================================================================

def get_known_words_path(lang: str) -> Path:
    return BASE_DIR / f"known_words_{lang}.json"


def get_themes_path(lang: str) -> Path:
    return BASE_DIR / f"themes_{lang}.json"


def get_db_path(lang: str) -> Path:
    return BASE_DIR / f"jezyki_{lang}.db"


def get_theme_state_path(lang: str) -> Path:
    return BASE_DIR / f"theme_state_{lang}.json"


def get_file_mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False)
def load_known_words_data(lang: str, mtime: float) -> list[str]:
    path = get_known_words_path(lang)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def load_known_lemmas(lang: str, mtime: float) -> set[str]:
    surface_words = load_known_words_data(lang, mtime)
    lemmas: set[str] = set()
    for w in surface_words:
        lemmas.update(lemmatize(w, lang))
    return lemmas


def get_themes_list(lang: str) -> list[str]:
    path = get_themes_path(lang)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("topics", [])
    except Exception:
        return []


def pick_topic(lang: str) -> str | None:
    topics = get_themes_list(lang)
    if not topics:
        return None
    state_path = get_theme_state_path(lang)
    last_topic = None
    if state_path.exists():
        try:
            last_topic = json.loads(state_path.read_text(encoding="utf-8")).get("last_topic")
        except Exception:
            last_topic = None
    candidates = [t for t in topics if t != last_topic] or topics
    chosen = random.choice(candidates)
    try:
        state_path.write_text(json.dumps({"last_topic": chosen}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return chosen


def get_previous_context(lang: str, max_chars: int = 300) -> str | None:
    db_path = get_db_path(lang)
    if not db_path.exists():
        return None
    conn = connect(str(db_path))
    row = conn.execute(
        "SELECT content FROM texts WHERE language = ? ORDER BY id DESC LIMIT 1", (lang,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    content = row[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+", content)
    tail = " ".join(sentences[-2:]) if len(sentences) >= 2 else content
    return tail[-max_chars:]


def get_lingq_api_key() -> str:
    # 1. Sprawdz st.secrets
    try:
        if "LINGQ_API_KEY" in st.secrets and st.secrets["LINGQ_API_KEY"]:
            return st.secrets["LINGQ_API_KEY"]
    except Exception:
        pass
    # 2. Sprawdz session_state
    return st.session_state.get("custom_lingq_api_key", "")


def get_gemini_api_key() -> str:
    # 1. Sprawdz st.secrets
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # 2. Sprawdz session_state
    return st.session_state.get("custom_gemini_api_key", "")


# ==============================================================================
# Pasek boczny: Wybor jezyka i status slownictwa
# ==============================================================================

st.sidebar.title("📚 Silnik i+1")

selected_lang = st.sidebar.selectbox(
    "Wybierz jezyk nauki:",
    options=list(LANG_CONFIG.keys()),
    format_func=lambda x: f"{LANG_CONFIG[x]['flag']} {LANG_CONFIG[x]['name']} ({x})",
    index=0,
)

lang_info = LANG_CONFIG[selected_lang]
known_path = get_known_words_path(selected_lang)
mtime = get_file_mtime(known_path)
known_words = load_known_words_data(selected_lang, mtime)
known_lemmas = load_known_lemmas(selected_lang, mtime)

st.sidebar.markdown("---")
st.sidebar.markdown(f"### Statystyki ({lang_info['flag']} {lang_info['name']})")
col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("Znane formy", len(known_words))
col_s2.metric("Unikalne lematy", len(known_lemmas))

# Liczba lekcji w bazie
db_path = get_db_path(selected_lang)
lesson_count = 0
if db_path.exists():
    try:
        conn = connect(str(db_path))
        row = conn.execute("SELECT COUNT(*) FROM texts WHERE language = ?", (selected_lang,)).fetchone()
        lesson_count = row[0] if row else 0
        conn.close()
    except Exception:
        lesson_count = 0
st.sidebar.metric("Ukonczone lekcje w bazie", lesson_count)

# ==============================================================================
# Panel boczny: Klucz Gemini (generowanie automatyczne)
# ==============================================================================

st.sidebar.markdown("---")
with st.sidebar.expander("✨ Automatyczne generowanie (Gemini)", expanded=False):
    has_gemini_secret = False
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            has_gemini_secret = True
    except Exception:
        pass

    if has_gemini_secret:
        st.caption("🔑 Klucz API wczytany z konfiguracji Secrets.")
    else:
        gemini_input = st.text_input(
            "Klucz API Gemini:",
            value=st.session_state.get("custom_gemini_api_key", ""),
            type="password",
            help="Pobierz klucz z: https://aistudio.google.com/apikey",
        )
        if gemini_input != st.session_state.get("custom_gemini_api_key", ""):
            st.session_state["custom_gemini_api_key"] = gemini_input

    selected_gemini_model = st.selectbox(
        "Model Gemini:",
        options=["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite"],
        index=0,
        help="gemini-3.6-flash jest domyslnym, najszybszym i stabilnym modelem z bezplatnym Free Tier w AI Studio.",
    )

    gemini_key_available = bool(get_gemini_api_key())
    st.caption(
        "✅ Klucz ustawiony - dostepny przycisk automatycznego generowania."
        if gemini_key_available
        else "Brak klucza - dostepne bedzie tylko generowanie recznego promptu."
    )

# ==============================================================================
# Panel boczny: Synchronizacja z LingQ
# ==============================================================================

st.sidebar.markdown("---")
with st.sidebar.expander("🔄 Synchronizacja z LingQ", expanded=False):
    current_key = get_lingq_api_key()
    has_secret_key = False
    try:
        if "LINGQ_API_KEY" in st.secrets and st.secrets["LINGQ_API_KEY"]:
            has_secret_key = True
    except Exception:
        pass

    if has_secret_key:
        st.caption("🔑 Klucz API wczytany z konfiguracji Secrets.")
    else:
        lingq_input = st.text_input(
            "Klucz API LingQ:",
            value=st.session_state.get("custom_lingq_api_key", ""),
            type="password",
            help="Pobierz klucz z: https://www.lingq.com/en/accounts/apikey/",
        )
        if lingq_input != st.session_state.get("custom_lingq_api_key", ""):
            st.session_state["custom_lingq_api_key"] = lingq_input

    api_key_to_use = get_lingq_api_key()

    if st.button("Pobierz slowa z LingQ", use_container_width=True):
        if not api_key_to_use:
            st.error("Brak klucza API LingQ. Wpisz klucz powyzej lub ustaw w secrets.toml.")
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def _ui_progress(i, total, count):
                pct = float(i) / float(max(total, 1))
                progress_bar.progress(pct)
                status_text.text(f"Pobieranie lekcji {i}/{total} - zebrano {count} slow known...")

            try:
                with st.spinner("Skanowanie konta LingQ..."):
                    words_set, counts = scan_known_words(
                        api_key=api_key_to_use,
                        language_code=selected_lang,
                        progress_callback=_ui_progress,
                    )
                
                # Zapis do pliku
                sorted_words = sorted(words_set)
                known_path.write_text(json.dumps(sorted_words, ensure_ascii=False, indent=2), encoding="utf-8")
                
                # Wyczyszczenie cache Streamlit
                st.cache_data.clear()
                
                progress_bar.progress(1.0)
                status_text.success(f"Pobrano {len(sorted_words)} unikalnych slow known z LingQ!")
                st.rerun()
            except Exception as e:
                st.error(f"Blad synchronizacji: {e}")

# ==============================================================================
# Panel glowny: Zakladki aplikacji
# ==============================================================================

st.title(f"{lang_info['flag']} Silnik i+1: {lang_info['name']}")
st.caption("Precyzyjnie kontrolowane generowanie lekcji jezykowych w oparciu o analize luk frekwencyjnych Zipf.")

tab_gen, tab_history, tab_vocab = st.tabs([
    "📝 Generator i walidator lekcji",
    "📚 Historia ukonczonych lekcji",
    "📊 Przeglad slownictwa i eksport",
])

# ------------------------------------------------------------------------------
# TAB 1: Generator i walidator
# ------------------------------------------------------------------------------
with tab_gen:
    if len(known_lemmas) == 0:
        st.warning(
            f"Brak zapisanych znanych slow dla jezyka {lang_info['name']}. "
            f"Uzyj panelu 'Synchronizacja z LingQ' po lewej stronie, aby pobrac baze slow ze swojego konta."
        )

    # Sekcja 1: Konfiguracja parametrów
    with st.expander("⚙️ Opcje generowania lekcji", expanded=True):
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        
        with col_cfg1:
            n_target = st.slider("Liczba nowych slow (target words):", min_value=3, max_value=15, value=8)
            min_occ = st.slider("Min. powtorzen per target word:", min_value=1, max_value=4, value=2)
            
        with col_cfg2:
            length_hint = st.selectbox(
                "Dlugosc tekstu:",
                ["500-800 slow", "800-1200 slow", "1200-1500 slow", "1500-2000 slow"],
                index=0,
            )
            serial_mode = st.checkbox(
                "Tryb serialu (Maciek i Damian, thriller)", value=True,
                help="Wylacz, zeby wrocic do prostego, niefabularnego cwiczenia i+1.",
            )

        with col_cfg3:
            continue_story = st.checkbox("Kontynuuj poprzednia historie", value=True)
            prev_context = get_previous_context(selected_lang) if continue_story else None
            if prev_context:
                st.caption(f"Poprzedni fragment: *\"{prev_context}\"*")
            elif continue_story:
                st.caption("Brak poprzednich tekstow w bazie - rozpoczecie nowej historii.")

        if serial_mode:
            db_path_for_settings = get_db_path(selected_lang)
            used_settings_list = []
            if db_path_for_settings.exists():
                conn_s = connect(str(db_path_for_settings))
                used_settings_list = get_used_settings(conn_s, selected_lang, limit=15)
                conn_s.close()
            if used_settings_list:
                st.caption(
                    "Miejsca juz odwiedzone (model unika ich automatycznie): "
                    + ", ".join(used_settings_list)
                )
            else:
                st.caption("Brak jeszcze odwiedzonych miejsc - model sam wybierze pierwsze.")
        else:
            # Tryb klasyczny (bez fabuly) - stary UI tematu
            st.markdown("**Temat lekcji:**")
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                custom_topic = st.text_input(
                    "Wlasny temat (opcjonalny, pozostaw puste dla losowania):",
                    placeholder="np. szpiegostwo w Berlinie Zachodnim lub kulisy meczu",
                )
            with col_t2:
                auto_topic = pick_topic(selected_lang)
                st.caption(f"Wylosowany temat domyslny:\n**{auto_topic or 'Brak pliku themes'}**")

    # Przycisk generowania
    col_btn1, col_btn2, _ = st.columns([1.3, 1.3, 2])
    with col_btn1:
        generate_clicked = st.button("✨ Generuj prompt lekcji", type="primary", use_container_width=True)
    with col_btn2:
        gemini_ready = bool(get_gemini_api_key())
        generate_auto_clicked = st.button(
            "🚀 Generuj i zapisz automatycznie (Gemini)",
            type="primary" if gemini_ready else "secondary",
            use_container_width=True,
            disabled=not gemini_ready,
            help=None if gemini_ready else "Ustaw klucz API Gemini w panelu bocznym, zeby odblokowac ten przycisk.",
        )

    if generate_clicked or generate_auto_clicked:
        if len(known_lemmas) == 0:
            st.error("Nie mozna wygenerowac lekcji bez listy znanych slow. Pobierz slowa z LingQ.")
        else:
            with st.spinner("Dobieranie optymalnych slow target words (Zipf) i budowanie promptu..."):
                src = WordfreqSource(selected_lang)
                target_lemmas = pick_next_unknown_words(
                    src, known_lemmas, selected_lang, n=n_target
                )

                if serial_mode:
                    api_key_for_scan = get_lingq_api_key()
                    in_progress = []
                    if api_key_for_scan:
                        try:
                            in_progress = get_in_progress_lemmas(
                                api_key_for_scan, selected_lang, selected_lang,
                                exclude_lemmas=known_lemmas | set(target_lemmas), n=6,
                            )
                        except Exception:
                            in_progress = []
                    prompt = build_thriller_prompt(
                        known_lemmas=list(known_lemmas),
                        target_lemmas=target_lemmas,
                        language=selected_lang,
                        in_progress_lemmas=in_progress,
                        min_target_occurrences=min_occ,
                        length_hint=length_hint,
                        used_settings=used_settings_list,
                        previous_context=prev_context,
                    )
                    chosen_topic = None
                else:
                    chosen_topic = custom_topic.strip() if custom_topic.strip() else auto_topic
                    prompt = build_gap_prompt(
                        known_lemmas=list(known_lemmas),
                        target_lemmas=target_lemmas,
                        language=selected_lang,
                        min_target_occurrences=min_occ,
                        length_hint=length_hint,
                        topic=chosen_topic,
                        previous_context=prev_context,
                    )

                st.session_state[f"prompt_{selected_lang}"] = prompt
                st.session_state[f"target_lemmas_{selected_lang}"] = target_lemmas
                st.session_state[f"min_occ_{selected_lang}"] = min_occ
                st.session_state[f"chosen_topic_{selected_lang}"] = chosen_topic

            if generate_auto_clicked:
                gemini_key = get_gemini_api_key()
                with st.spinner("Gemini pisze i w razie potrzeby poprawia odcinek (moze to potrwac do minuty)..."):
                    try:
                        from gemini_client import generate_and_validate_lesson
                        cleaned_text, extracted_setting, auto_result, repairs, used_model = generate_and_validate_lesson(
                            gemini_key, prompt, selected_lang, known_lemmas, target_lemmas,
                            min_target_occurrences=min_occ,
                            model_id=selected_gemini_model,
                        )
                        st.session_state[f"response_area_{selected_lang}"] = cleaned_text
                        st.session_state[f"extracted_setting_{selected_lang}"] = extracted_setting
                        st.session_state[f"auto_validate_{selected_lang}"] = True
                        if used_model != selected_gemini_model:
                            st.info(f"Model {selected_gemini_model} byl przeciazony - automatycznie uzyto {used_model}.")
                        if extracted_setting:
                            st.caption(f"Miejsce akcji wybrane przez model: **{extracted_setting}**")
                        if repairs > 0:
                            st.info(f"Model potrzebowal {repairs} automatycznej/-ych poprawki/poprawek.")
                        if not auto_result["ok"]:
                            st.warning(
                                "Nawet po automatycznych poprawkach tekst wciaz ma naruszenia - "
                                "zobacz szczegoly w sekcji walidacji ponizej."
                            )
                    except Exception as e:
                        st.error(f"Blad generowania przez Gemini: {e}")

    # Wyswietlanie wygenerowanego promptu
    prompt_key = f"prompt_{selected_lang}"
    if prompt_key in st.session_state:
        st.markdown("---")
        st.subheader("1. Wygenerowany prompt i+1")
        
        target_list = st.session_state.get(f"target_lemmas_{selected_lang}", [])
        src = WordfreqSource(selected_lang)
        
        st.markdown("**Nowe slowa (target words) wybrane dla tej lekcji:**")
        cols = st.columns(min(len(target_list), 4))
        for i, word in enumerate(target_list):
            z_score = src.zipf(word)
            col_idx = i % len(cols)
            cols[col_idx].info(f"**{word}**  \nZipf: `{z_score:.2f}`")

        st.caption("Skopiuj ponizszy prompt za pomoca ikony w prawym gornym rogu ramki, wklej do modelu (Claude, ChatGPT, Gemini), a nastepnie wklej odpowiedz ponizej:")
        st.code(st.session_state[prompt_key], language="markdown")

    # Sekcja walidacji odpowiedzi
    st.markdown("---")
    st.subheader("2. Weryfikacja i zapis odpowiedzi modelu")
    
    response_text = st.text_area(
        "Wklej wygenerowany tekst z modelu:",
        height=220,
        placeholder="Wklej tutaj tekst wygenerowany przez Claude / ChatGPT / Gemini...",
        key=f"response_area_{selected_lang}",
    )

    col_v1, col_v2 = st.columns([1, 3])
    with col_v1:
        validate_clicked = st.button("🧪 Zwaliduj i zapisz", type="primary", use_container_width=True)

    validate_clicked = validate_clicked or st.session_state.pop(f"auto_validate_{selected_lang}", False)

    if validate_clicked:
        if not response_text.strip():
            st.error("Wklej tekst odpowiedzi modelu przed uruchomieniem walidacji.")
        else:
            targets = st.session_state.get(f"target_lemmas_{selected_lang}", [])
            min_o = st.session_state.get(f"min_occ_{selected_lang}", 2)

            # Wyciagnij "MIEJSCE_AKCJI: ..." jesli jest (np. z recznie wklejonej
            # odpowiedzi z innego modelu) - inaczej ta linia falszywie zaliczylaby
            # sie jako naruszenie slownictwa. W trybie auto tekst jest juz czysty.
            cleaned_response, pasted_setting = extract_setting_from_text(response_text)
            final_setting = pasted_setting or st.session_state.get(f"extracted_setting_{selected_lang}")

            with st.spinner("Analiza lematyzacyjna i sprawdzanie ograniczen leksykalnych..."):
                val_res = validate_generated_text(
                    text=cleaned_response,
                    language=selected_lang,
                    allowed_lemmas=known_lemmas,
                    target_lemmas=targets,
                    min_target_occurrences=min_o,
                )
                
                # Zapisanie wyniku do session_state
                st.session_state[f"val_res_{selected_lang}"] = val_res

            # Prezentacja wynikow walidacji
            if val_res["ok"]:
                st.success("✅ Tekst w 100% zgodny z ograniczeniami leksykalnymi i+1!")
                conn = connect(str(get_db_path(selected_lang)))
                save_text(conn, selected_lang, cleaned_response, targets, setting=final_setting)
                
                # Obliczenie i zalogowanie pokrycia
                text_lemmas = lemmatize(cleaned_response, selected_lang)
                cov = text_coverage(text_lemmas, known_lemmas | set(targets))
                log_coverage(conn, selected_lang, cov["token_coverage"], cov["type_coverage"], sample_size=cov["sample_size"])
                conn.close()
                
                st.info("💾 Tekst zostal pomyslnie zapisany w bazie historii. Kolejna lekcja bedzie kontynuowac te fabule.")
            else:
                st.error("❌ Tekst zawiera naruszenia ograniczen leksykalnych.")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.markdown("#### Niedozwolone slowa (spoza listy znanych i target):")
                    if val_res["violations"]:
                        v_data = [{"Slowo/Lemat": k, "Liczba uzyc": v} for k, v in val_res["violations"].items()]
                        st.dataframe(v_data, use_container_width=True)
                    else:
                        st.caption("Brak niedozwolonych slow.")

                with col_res2:
                    st.markdown("#### Uzycie target words:")
                    tc_data = [
                        {"Target word": k, "Wystapienia": v, "Status": "✅ OK" if v >= min_o else f"❌ Za malo (min. {min_o})"}
                        for k, v in val_res["target_coverage"].items()
                    ]
                    st.dataframe(tc_data, use_container_width=True)

                st.markdown("---")
                st.markdown("**Prompt do poprawki (wklej do modelu):**")
                fix_prompt = (
                    f"Twoj poprzedni tekst zawiera nastepujace naruszenia:\n"
                    + (f"- Uzyto niedozwolonych slow spoza listy: {list(val_res['violations'].keys())}\n" if val_res['violations'] else "")
                    + (f"- Zbyt malo wystapien target words (wymagane min. {min_o}): {val_res['missing_targets']}\n" if val_res['missing_targets'] else "")
                    + "Przepisz tekst, eliminujac powyzsze bledy i scisle przestrzegajac podanych ograniczen leksykalnych."
                )
                st.code(fix_prompt, language="markdown")

                # Opcjonalny wymuszony zapis
                if st.button("⚠️ Zapisz mimo ostrzezen (force save)"):
                    conn = connect(str(get_db_path(selected_lang)))
                    save_text(conn, selected_lang, cleaned_response, targets, setting=final_setting)
                    conn.close()
                    st.warning("Tekst zostal zapisany na wyrazne zadanie.")


# ------------------------------------------------------------------------------
# TAB 2: Historia ukonczonych lekcji
# ------------------------------------------------------------------------------
with tab_history:
    st.subheader(f"Historia wygenerowanych tekstow ({lang_info['flag']} {lang_info['name']})")
    
    db_file = get_db_path(selected_lang)
    if not db_file.exists():
        st.info("Baza danych jest pusta. Wygeneruj i zapisz swoja pierwsza lekcje.")
    else:
        conn = connect(str(db_file))
        texts = get_recent_texts(conn, selected_lang, limit=30)
        conn.close()

        if not texts:
            st.info("Brak zapisanych lekcji dla tego jezyka.")
        else:
            st.write(f"Liczba zapisanych tekstow: **{len(texts)}**")
            for item in texts:
                date_str = item.get("date", "Brak daty")
                t_words = ", ".join(item.get("target_words", [])) or "Brak"
                setting_label = item.get("setting") or "nieznane"
                with st.expander(f"📖 Lekcja #{item['id']} - {date_str} - {setting_label}"):
                    st.markdown(f"**Miejsce akcji:** {setting_label}")
                    st.markdown(f"**Target words:** `{t_words}`")
                    st.text_area("Tresc lekcji:", value=item["content"], height=160, key=f"hist_{item['id']}")


# ------------------------------------------------------------------------------
# TAB 3: Przeglad slownictwa i eksport
# ------------------------------------------------------------------------------
with tab_vocab:
    st.subheader("Przeglad bazy leksykalnej")
    
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        search_query = st.text_input("Szukaj w znanych lematach:", placeholder="np. haus, gehen...")
        if search_query:
            q = search_query.strip().lower()
            matching = [l for l in sorted(known_lemmas) if q in l]
            st.write(f"Znaleziono **{len(matching)}** pasujacych lematow:")
            st.write(", ".join(matching[:100]))
        else:
            st.caption(f"Lacznie w bazie: {len(known_lemmas)} unikalnych lematow.")

    with col_v2:
        st.markdown("#### Kopia zapasowa")
        if known_words:
            json_bytes = json.dumps(known_words, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                label=f"💾 Pobierz known_words_{selected_lang}.json",
                data=json_bytes,
                file_name=f"known_words_{selected_lang}.json",
                mime="application/json",
                use_container_width=True,
            )
        
        if db_path.exists():
            db_bytes = db_path.read_bytes()
            st.download_button(
                label=f"💾 Pobierz jezyki_{selected_lang}.db",
                data=db_bytes,
                file_name=f"jezyki_{selected_lang}.db",
                mime="application/x-sqlite3",
                use_container_width=True,
            )
