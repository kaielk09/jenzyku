# 321 AI Creator v2

## Co działa
- Konto GitHub łączy się przez oficjalne GitHub CLI (gh); aplikacja nie zbiera haseł ani tokenów.
- Projekt, konfiguracja, checkpointy i końcowe wagi trafiają do Pulpit/321 AI Models/<nazwa>.
- Kreator pozwala ustawić zadania tekstowe: programowanie, rozmowa i rozumowanie, ich docelowe liczby przykładów oraz parametry architektury i treningu.
- Trening uruchamia się z GUI, a logi i postęp są pokazywane w oknie.
- Po treningu, jeśli GitHub jest połączony, aplikacja publikuje projekt przez gh repo create. Repozytorium prywatne jest domyślnym ustawieniem.
- Wagi końcowe: model/model.pt; metadane: model/model_info.json; wznowienie: checkpoints/latest.pt.

## Dane i rzeczywiste proporcje zadań
Obsługiwane formaty: TXT, MD, JSONL i CSV. Dla osobnego bilansowania zadań używaj JSONL lub CSV z polem category, task, type albo tag. Rozpoznawane etykiety:
- programowanie: programming, code, coding, developer
- rozmowa: conversation, chat, dialogue
- rozumowanie: reasoning, logic, math, problem_solving

Przykład JSONL (jeden rekord na linię):
```json
{"category":"programowanie","prompt":"Napisz funkcję sumującą","completion":"def add(a, b): return a + b"}
{"category":"rozmowa","prompt":"Cześć","completion":"Witaj!"}
{"category":"rozumowanie","prompt":"Ile to 17 + 25?","completion":"42"}
```

Kreatorowe liczby task mix są teraz stosowane jako docelowe liczby przykładów w korpusie treningowym. Jeśli danych w kategorii jest mniej, rekordy są powtarzane z deterministycznym losowaniem. Jeśli kategoria nie ma rekordów, ale istnieje zwykły tekst bez etykiety, może zostać użyty jako wspólny tekst ogólny — log treningu wyświetli ostrzeżenie. Nieoznaczonego tekstu nie należy traktować jako specjalistycznych danych programistycznych/rozumowania. Gdy nie ma ani kategorii, ani tekstu ogólnego, trening zatrzyma się z czytelnym błędem.

## Ograniczenia, których nie ukrywamy
- 321-TinyGPT to eksperymentalny, byte-level model tekstowy trenowany od zera; nie jest modelem foundation ani odpowiednikiem dużych asystentów.
- Obecny pipeline uczy jeden wspólny model tekstowy na zbalansowanym strumieniu. Nie tworzy trzech niezależnych modeli.
- Generowanie obrazów nie jest dostępne; wymaga osobnej architektury, danych i testów.
- Wbudowany zestaw startowy jest demonstracyjny, a nie jakościowym korpusem do produkcyjnego modelu.
- Samo ukończenie treningu nie gwarantuje dobrej jakości. Wynik zależy od praw, jakości, różnorodności i rozmiaru danych oraz sprzętu.
