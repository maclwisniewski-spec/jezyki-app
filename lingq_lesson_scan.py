"""
lingq_lesson_scan.py

Dzialajaca metoda pobrania pelnej listy known words z LingQ (patrz
wyjasnienie w sekcji "Kluczowe odkrycie techniczne" powyzej).
"""
from __future__ import annotations
import time
from collections import Counter
from typing import Any

import requests

API_BASE = "https://www.lingq.com/api/v3/{lang}"


def list_collection_ids(api_key: str, language_code: str) -> list[int]:
    headers = {"Authorization": f"Token {api_key}"}
    url = f"{API_BASE.format(lang=language_code)}/collections/my/"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return [c["id"] for c in resp.json().get("results", [])]


def list_lesson_ids(api_key: str, language_code: str, sleep_between_calls: float = 0.3) -> list[int]:
    headers = {"Authorization": f"Token {api_key}"}
    lesson_ids: list[int] = []
    for cid in list_collection_ids(api_key, language_code):
        url = f"{API_BASE.format(lang=language_code)}/collections/{cid}/lessons/"
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        lesson_ids.extend(l["id"] for l in resp.json().get("results", []))
        time.sleep(sleep_between_calls)
    return lesson_ids


def scan_known_words(
    api_key: str,
    language_code: str,
    sleep_between_calls: float = 0.3,
    progress_callback=None,
) -> tuple[set[str], Counter]:
    headers = {"Authorization": f"Token {api_key}"}
    lesson_ids = list_lesson_ids(api_key, language_code, sleep_between_calls)

    known_words: set[str] = set()
    status_counts: Counter = Counter()

    for i, lid in enumerate(lesson_ids):
        url = f"{API_BASE.format(lang=language_code)}/lessons/{lid}/"
        resp = requests.get(url, headers=headers, timeout=25)
        if resp.status_code != 200:
            continue
        words = resp.json().get("words", {}) or {}
        for w in words.values():
            status = w.get("status")
            status_counts[status] += 1
            if status == "known":
                known_words.add(w["text"].lower())
        time.sleep(sleep_between_calls)
        if progress_callback:
            progress_callback(i + 1, len(lesson_ids), len(known_words))

    return known_words, status_counts


def scan_known_lemmas(api_key: str, language_code: str, spacy_lang_code: str, **kwargs) -> set[str]:
    from lemmatize import lemmatize
    surface_words, _ = scan_known_words(api_key, language_code, **kwargs)
    lemmas: set[str] = set()
    for w in surface_words:
        lemmas.update(lemmatize(w, spacy_lang_code))
    return lemmas


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) != 3:
        print("Uzycie: python lingq_lesson_scan.py <api_key> <language_code>")
        sys.exit(1)

    api_key, lang = sys.argv[1], sys.argv[2]

    def _progress(i, total, known_so_far):
        print(f"...{i}/{total} lekcji, known do tej pory: {known_so_far}")

    words, counts = scan_known_words(api_key, lang, progress_callback=_progress)
    print("STATUS COUNTS:", dict(counts))
    print("UNIKALNYCH known words:", len(words))

    out_path = f"known_words_{lang}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sorted(words), f, ensure_ascii=False, indent=2)
    print(f"Zapisano do {out_path}")
