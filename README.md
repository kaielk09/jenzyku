# 321code

**321code** is a Polish-first programming language and command-line tool. Source files use the `.321` extension. It also includes an experimental creator for training small language models from scratch.

## Instalacja

Wymagany jest Python 3.10 lub nowszy. Jednorazowo, w folderze repozytorium, zainstaluj 321code:

```bash
python -m pip install .
```

To polecenie instaluje środowisko. Później właściwe komendy użytkownika zaczynają się od `321`:

```bash
321 help
321 version
321 run examples/hello.321
321 ai
```

## 321 AI — tworzenie własnego modelu

`321 ai` otwiera okienkowy 321 AI Creator. Wybierasz nazwę modelu, liczbę kroków, opis GPU i plik TXT z danymi. Po kliknięciu CREATE MODEL program tworzy folder `ai/<nazwa-modelu>/` i rozpoczyna trening.

W folderze projektu znajdziesz:
- `config.json` — ustawienia modelu i treningu;
- `dataset.txt` — kopię wybranych danych treningowych;
- `model/model.pt` — zapis wytrenowanego modelu;
- `model/model_info.json` — informacje o modelu.

Model jest małym, eksperymentalnym GPT typu Transformer trenowanym od zera na bajtach tekstu. Nie jest gotowym dużym chatbotem i nie ma wiedzy, której nie zawierają dane treningowe. Jakość zależy przede wszystkim od wielkości, różnorodności i poprawności danych. Dla modelu rozmownego używaj wielu przykładów w formacie:

```text
Użytkownik: Ile to 2 + 2?
AI: 2 + 2 = 4.
Użytkownik: Czym jest fotosynteza?
AI: To proces, w którym rośliny wykorzystują światło do wytwarzania związków odżywczych.
```

Dane powinny być legalne do użycia, poprawne i zapisane w UTF-8. Wybierz plik TXT o wielkości co najmniej 512 bajtów. Mały przykładowy zbiór znajduje się w `examples/ai_training.txt`; służy tylko do sprawdzenia działania, nie do stworzenia dobrego, uniwersalnego AI.

### Wymagania i komendy AI

Trening wymaga PyTorch. Instalacja biblioteki jest jednorazową czynnością techniczną:

```bash
python -m pip install torch
```

Następnie wszystkie polecenia narzędzia AI zaczynają się od `321`:

```bash
321 ai              # otwórz kreator
321 ai help         # pokaż komendy AI
321 ai train ai/MojModel
321 ai chat ai/MojModel
```

GPU jest wykrywane automatycznie przez PyTorch. Nazwa GPU wpisana w kreatorze jest tylko informacyjna. Jeśli CUDA nie jest dostępna, trening użyje CPU. Duża liczba kroków może trwać bardzo długo, szczególnie na laptopie. Zacznij od małej liczby kroków i przerwij trening, jeśli komputer działa niestabilnie lub nadmiernie się nagrzewa.

Model i okno czatu są eksperymentalne. To nie jest odpowiednik ChatGPT, a samo zapisanie `model.pt` nie tworzy pliku EXE. Instalator EXE i dystrybucja modeli to osobne, przyszłe etapy.

## Przykład języka 321code

```321
let name = "Świecie"
let count = 0

def greet(person):
    print "Witaj, " + person

greet(name)

while count < 3:
    print count
    set count = count + 1
```

Uruchom: `321 run examples/hello.321`.

## Status projektu

Interpreter obsługuje zmienne, wyrażenia, warunki, pętle, funkcje i lokalne importy. Katalog komend jest nadal niewielki. Menedżer pakietów `321 install` jest placeholderem i nie pobiera paczek.

## Licencja

MIT. Zobacz `LICENSE`.
