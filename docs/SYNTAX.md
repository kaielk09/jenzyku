# Składnia 321code — wersja 0.2

Pliki źródłowe mają rozszerzenie `.321`. Bloki zapisuje się z wcięciem dokładnie 4 spacji.

## Tekst, zmienne i liczby

```321
let nick = "321code"
let punkty = 10
set punkty = punkty + 5
print "Witaj, " + nick
print punkty
```

`let` tworzy zmienną, a `set` zmienia jej wartość.

## Warunki

```321
if punkty >= 15:
    print "Masz co najmniej 15 punktów"
else:
    print "Trenuj dalej"
```

Obsługiwane porównania: `==`, `!=`, `<`, `<=`, `>`, `>=`. Logika: `and`, `or`, `not`.

## Pętle

```321
let licznik = 0
while licznik < 3:
    print licznik
    set licznik = licznik + 1

for i in range(3):
    print i
```

Pętle mają limit 10 000 powtórzeń, aby przypadkowy program nie zawiesił interpretera.

## Funkcje

```321
def przywitaj(imie):
    print "Cześć, " + imie
    return 1

przywitaj("Ala")
```

Funkcje obsługują parametry pozycyjne i `return`. Zagnieżdżenie wywołań jest ograniczone.

## Import modułu

```321
import "modul.321"
```

Import uruchamia plik z rozszerzeniem `.321` znajdujący się wewnątrz tego samego folderu projektu lub jego podfolderów. Importy cykliczne i wyjście poza folder projektu są blokowane.

## Komentarze

Linia zaczynająca się od `#` jest komentarzem.

## Ograniczenia wersji 0.2

To wciąż wczesny interpreter. Nie obsługuje jeszcze klas, obiektów, bibliotek zewnętrznych, własnych typów ani instalowania pakietów. Wyrażenia są obliczane przez ograniczony parser AST — kod 321code nie jest wykonywany przez Pythonowe `eval` ani `exec`.
