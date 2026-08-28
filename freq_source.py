"""
freq_source.py

Abstrakcja nad zrodlem czestotliwosci slow. Cel: silnik (coverage.py,
prompt_builder.py) nie jest zrosniety z konkretnie biblioteka wordfreq -
mozesz podmienic 'best' (rejestr mieszany: napisy filmowe + Wikipedia +
social media) na liste rejestrowo-specyficzna (pisana - prasa/Wikipedia,
albo mowiona - OpenSubtitles/SUBTLEX) bez zmiany reszty kodu.
"""
from __future__ import annotations
import math
import itertools
from typing import Protocol, Iterator, Iterable


class FrequencySource(Protocol):
    def zipf(self, word: str) -> float: ...
    def ranked_words(self, limit: int) -> Iterable[str]: ...


class WordfreqSource:
    """Domyslne, mieszane zrodlo (wordfreq: napisy + Wikipedia + social media)."""

    def __init__(self, language: str, wordlist: str = "best"):
        self.language = language
        self.wordlist = wordlist

    def zipf(self, word: str) -> float:
        from wordfreq import zipf_frequency
        return zipf_frequency(word, self.language, wordlist=self.wordlist)

    def ranked_words(self, limit: int = 50000) -> Iterator[str]:
        from wordfreq import iter_wordlist
        return itertools.islice(iter_wordlist(self.language, wordlist=self.wordlist), limit)


class CustomListSource:
    """Zrodlo rejestrowo-specyficzne wczytywane z pliku ('slowo liczba' per linia)."""

    def __init__(self, path: str):
        self._words: list[str] = []
        self._counts: dict[str, int] = {}
        total = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 2:
                    continue
                word, count_str = parts
                try:
                    count = int(count_str)
                except ValueError:
                    continue
                word = word.lower()
                self._words.append(word)
                self._counts[word] = self._counts.get(word, 0) + count
                total += count
        self._total = total

    def zipf(self, word: str) -> float:
        count = self._counts.get(word.lower(), 0)
        if count == 0 or self._total == 0:
            return 0.0
        freq_per_million = count / self._total * 1_000_000
        if freq_per_million <= 0:
            return 0.0
        return round(math.log10(freq_per_million) + 3, 2)

    def ranked_words(self, limit: int = 50000) -> Iterator[str]:
        return iter(self._words[:limit])
