# 321 AI Creator v2

- Konto GitHub łączy się przez oficjalne GitHub CLI (gh), bez zbierania haseł ani tokenów przez aplikację.
- Projekt i wagi trafiają do `Pulpit/321 AI Models/<nazwa>`.
- Kreator pozwala wybrać proporcje zadań tekstowych: programowanie, rozmowa, rozumowanie.
- Trening i logi są widoczne w GUI.
- Po treningu, jeśli konto jest połączone, aplikacja tworzy repozytorium i wypycha projekt przez `gh repo create`.
- Prywatne repozytorium jest domyślnie zalecane.

**Ograniczenia:** aktualny model 321-TinyGPT jest eksperymentalnym modelem tekstowym byte-level. Ustawienia task mix zapisują proporcje zadań w konfiguracji, ale nie są jeszcze osobnym nadzorowanym pipeline'em per zadanie. Generowanie obrazów wymaga osobnej architektury i nie jest dostępne w tej wersji. Zestaw startowy jest demonstracyjny, nie jest danymi do jakości komercyjnej.