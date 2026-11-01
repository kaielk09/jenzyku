# Składnia 321code — wersja 0.1

Pliki źródłowe mają rozszerzenie `.321`.

## Komentarze

Linia zaczynająca się od `#` jest komentarzem.

## Wyświetlanie tekstu

```321
print "Cześć!"
```

## Zmienne tekstowe

```321
let nick = "321code"
print "Witaj w " + nick
```

## Aktualne ograniczenia

Wersja 0.1 obsługuje instrukcje `print`, `let`, komentarze i proste łączenie tekstu. Zmienne są tekstowe. Pętle, warunki, funkcje, importy, typy liczbowe i obsługa modułów są zaplanowane, ale jeszcze niezaimplementowane.

Nie używaj `eval` ani nie uruchamiaj nieznanych skryptów jako sposobu rozszerzania języka. Nowe funkcje powinny być dodawane jako jawne, testowane instrukcje interpretera.
