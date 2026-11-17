# 321code

**321code** is a Polish-first programming language and command-line tool. Source files use the `.321` extension. It also includes an experimental creator for training small language models from scratch.

## Instalator Windows (bez Pythona na komputerze użytkownika)

W repozytorium znajduje się skrypt `build_windows.bat`. Na komputerze, na którym budujesz instalator, uruchom go dwuklikiem. Skrypt używa Pythona i PyInstallera wyłącznie do przygotowania plików EXE.

Po zbudowaniu znajdziesz:
- `dist/321code-Setup.exe` — instalator z oknem i przyciskiem **Zainstaluj**;
- `dist/321.exe` — samodzielny interpreter języka.

Na komputerze docelowym nie trzeba instalować Pythona. Uruchom `321code-Setup.exe`, kliknij **Zainstaluj**. Program kopiuje interpreter do `%LOCALAPPDATA%\\Programs\\321code\\bin` i dopisuje ten folder do zmiennej PATH bieżącego użytkownika. Po pomyślnej instalacji instalator usuwa swój plik EXE; zainstalowany `321.exe` pozostaje na komputerze.

Następnie otwórz nowe okno CMD i używaj:

```bat
321 help
321 version
321 run C:\sciezka\do\pliku.321
321 ai
```

**Uwaga:** skrypt BAT buduje instalator na Windows. Nie jest to gotowy plik EXE przechowywany w repozytorium — EXE powstaje dopiero po uruchomieniu skryptu. Build nie został jeszcze potwierdzony na rzeczywistym komputerze Windows.

## 321 AI — tworzenie własnego modelu

`321 ai` otwiera okienkowy 321 AI Creator. Wybierasz nazwę modelu, liczbę kroków, opis GPU i plik TXT z danymi. Po kliknięciu CREATE MODEL program tworzy folder `ai/<nazwa-modelu>/` i rozpoczyna trening.

W folderze projektu znajdziesz:
- `config.json` — ustawienia modelu i treningu;
- `dataset.txt` — kopię wybranych danych treningowych;
- `model/model.pt` — zapis wytrenowanego modelu;
- `model/model_info.json` — informacje o modelu.

Model jest małym, eksperymentalnym GPT typu causal Transformer trenowanym od zera na bajtach UTF-8. To własna architektura 321code, a nie gotowy duży chatbot. Nie ma wiedzy, której nie zawierają dane treningowe. Jakość zależy przede wszystkim od jakości, różnorodności i wielkości danych. Trening obsługuje podział trening/walidacja, losowe batch'e, gradient accumulation, cosine learning-rate schedule, clipping gradientów, checkpointy latest/best i wznowienie treningu. Dla modelu rozmownego używaj wielu przykładów w formacie:

```text
Użytkownik: Ile to 2 + 2?
AI: 2 + 2 = 4.
Użytkownik: Czym jest fotosynteza?
AI: To proces, w którym rośliny wykorzystują światło do wytwarzania związków odżywczych.
```

Dane powinny być legalne do użycia, poprawne i zapisane w UTF-8. Wybierz plik TXT o wielkości co najmniej 2048 bajtów; praktycznie potrzeba znacznie więcej danych niż minimum techniczne. Trening zapisuje `checkpoints/latest.pt`, `checkpoints/best.pt`, `training_metrics.jsonl`, `model/model.pt` i `model/model_info.json`. Mały przykładowy zbiór znajduje się w `examples/ai_training.txt`; służy tylko do sprawdzenia działania, nie do stworzenia dobrego, uniwersalnego AI.

### Wymagania i komendy AI

Trening wymaga PyTorch. W obecnej wersji moduł treningowy wymaga osobnej instalacji biblioteki PyTorch na komputerze użytkownika, więc samodzielny interpreter EXE nie oznacza jeszcze, że cały trening AI działa bez dodatkowych bibliotek.

```bat
321 ai
321 ai help
321 ai train ai/MojModel
321 ai chat ai/MojModel
```

GPU jest wykrywane automatycznie przez PyTorch. Nazwa GPU wpisana w kreatorze jest tylko informacyjna. Jeśli CUDA nie jest dostępna, trening użyje CPU. Duża liczba kroków może trwać bardzo długo, szczególnie na laptopie. Checkpoint pozwala wznowić trening po przerwaniu. Czat zachowuje kilka ostatnich wymian w kontekście, ale mały model nadal może generować błędny lub niezrozumiały tekst.


## Instalacja z CMD przez Python lub Javę

### Python (Python 3.10+)

Pobierz plik `install_321.py` z repozytorium i uruchom:

```bat
py install_321.py
```

Skrypt używa aktualnego interpretera Pythona i `pip`, aby pobrać oraz zainstalować 321code z GitHuba. Po instalacji otwórz nowe CMD i wpisz `321 help`.

Możesz też zainstalować bez pobierania skryptu:

```bat
py -m pip install --upgrade git+https://github.com/kaielk09/jenzyku.git
```

### Java (Java 11+ na Windows)

Pobierz plik `Install321.java` z repozytorium, a następnie uruchom w CMD:

```bat
java Install321.java
```

Program Java pobierze oficjalny `321code-Setup.exe` z repozytorium GitHub i automatycznie go uruchomi. W oknie instalatora kliknij **Zainstaluj**. Java nie zastępuje Pythona do uruchamiania wersji źródłowej — ten sposób uruchamia gotowy instalator Windows.

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

Interpreter obsługuje zmienne, wyrażenia, warunki, pętle while i for, funkcje, lokalne importy, listy, krotki, słowniki oraz odczyt elementów przez indeks lub klucz. Funkcje wbudowane: str(), int(), float(), bool(), len(), abs(), min(), max(), round(), range(), upper(), lower() i input(). Konsola CMD ma kolorowe komunikaty pomocy, sukcesu, informacji i błędów. Katalog komend jest nadal niewielki. Menedżer pakietów obsługuje lokalne archiwa ZIP, rejestr HTTPS, kontrolę SHA-256, zależności, listę pakietów, usuwanie, aktualizacje, pakowanie i plik blokady `321code.lock`. Rejestr startuje pusty — instalacja pakietów po nazwie zacznie działać, gdy zostaną opublikowane wpisy z prawidłowym archiwum i sumą SHA-256.

## Menedżer pakietów 321 Packages

W folderze projektu (tam, gdzie znajduje się `321code.json`) używaj:

```bat
321 packages init ./moj-pakiet mojpakiet
321 packages pack ./moj-pakiet
321 install ./mojpakiet-1.0.0.zip
321 packages list
321 packages remove mojpakiet
321 packages update
321 packages help
```

Możesz też zainstalować lokalny plik ZIP:

```bat
321 install C:\\sciezka\\do\\pakietu.zip
```

Każdy pakiet musi zawierać `package.json` z nazwą i wersją oraz co najmniej jeden plik `.321`. Pakiety są instalowane do `.321code/packages/`, a dokładne wersje i sumy SHA-256 trafiają do `321code.lock`. Import modułu pakietu wygląda tak:

```321
import "hello321/main.321"
```

Menedżer sprawdza sumę SHA-256 archiwum, ogranicza rozmiar pobierania i rozpakowywania oraz odrzuca ścieżki wychodzące poza archiwum i dowiązania symboliczne. Rejestr jest hostowany w `packages/index.json`; początkowo jest pusty, więc instalowanie po nazwie wymaga najpierw opublikowania pakietów przez utrzymujących rejestr. Format publikacji opisano w `packages/README.md`.

## Licencja

MIT. Zobacz `LICENSE`.
