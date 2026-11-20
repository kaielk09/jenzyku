"""Intent parsing for the experimental 321 AI dataset builder.

This is rule-based (not a trained language model): it identifies likely goal/format
and expands a web search query into a focused topic.
"""
from __future__ import annotations
import re

def understand_request(prompt: str) -> dict:
    raw = prompt.strip()
    if not raw:
        raise ValueError("Polecenie jest puste.")
    p = raw.lower()
    file_type = "dataset"
    if re.search(r"\b(txt|tekst|dane|zbior|dataset|trening|train)\b", p):
        file_type = "training_text"
    elif re.search(r"\b(kod|program|python|javascript|script|skrypt)\b", p):
        file_type = "code_reference"
    elif re.search(r"\b(opis|wyjaśnij|wytłumacz|definicja|description)\b", p):
        file_type = "explanation_reference"

    # Simple topic/category hints used to refine search without altering the user's intent.
    category = "ogólny"
    hints = [
        (("python", "programowanie", "kod", "skrypt", "javascript", "java"), "programowanie"),
        (("minecraft", "mod", "modowanie"), "Minecraft/modowanie"),
        (("historia", "historyczny", "wojna", "król", "królowie"), "historia"),
        (("matematyka", "algebra", "geometria", "równanie"), "matematyka"),
        (("biologia", "organizm", "komórka", "ekosystem"), "biologia"),
        (("fizyka", "energia", "ruch", "siła"), "fizyka"),
    ]
    for words, label in hints:
        if any(w in p for w in words):
            category = label
            break
    # Keep the query simple and don't append category guesses when user supplied a precise topic.
    search_query = raw
    if category != "ogólny":
        search_query = f"{raw} podstawowe informacje przykłady"
    return {
        "original": raw,
        "intent": file_type,
        "category": category,
        "search_query": search_query,
        "output_format": "TXT",
        "needs_web": True,
        "note": "Rule-based intent detection; not an LLM.",
    }
