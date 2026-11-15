# 321 AI Creator v2 — funkcje i ograniczenia

## Instalacja dodatków
- API HTTP: `py -m pip install ".[api]"`
- Hugging Face: `py -m pip install ".[huggingface]"`
- model obrazowy: `py -m pip install ".[images]"`
- wszystkie moduły AI: `py -m pip install ".[all-ai]"`

PyTorch musi mieć build zgodny z posiadanym CPU/GPU. Wybór CUDA nie instaluje sterowników ani CUDA automatycznie.

## Model tekstowy i dane
Kreator `321 ai` zapisuje projekt do Pulpit/321 AI Models. Task mix stosuje docelowe liczby rekordów w zbalansowanym strumieniu treningowym. Dla prawdziwego balansu używaj JSONL/CSV z polem category/task/type/tag.

```json
{"category":"programowanie","prompt":"Napisz funkcję sumującą","completion":"def add(a,b): return a+b"}
{"category":"rozmowa","prompt":"Cześć","completion":"Witaj"}
{"category":"rozumowanie","prompt":"17+25","completion":"42"}
```

Kategorie: programowanie (programming/code/coding/developer), rozmowa (conversation/chat/dialogue), rozumowanie (reasoning/logic/math/problem_solving). Jeśli kategorii brakuje, ogólny tekst może zostać użyty jako wspólny materiał, a log pokaże ostrzeżenie. Powtarzanie przykładów nie tworzy nowych informacji.

## Pobieranie datasetu z Hugging Face
```bat
321 ai download-dataset OWNER/DATASET dataset.jsonl --max-examples 100000
```
Automatyczny filtr dopuszcza licencje MIT, Apache-2.0, BSD-2/3-Clause, CC0-1.0, CC-BY-4.0, CC-BY-SA-4.0 i ISC. Brak licencji lub inna licencja oznacza odmowę. To filtr techniczny, nie porada prawna — przed treningiem sprawdź prawa do treści i wymagania atrybucji. Dane są pobierane strumieniowo do JSONL.

## Lokalne API HTTP
```bat
py -m pip install ".[api]"
321 ai serve "C:\sciezka\do\modelu"
```
Domyślnie API słucha tylko na `127.0.0.1:8000`. Endpointy: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`.

Aby udostępnić API w sieci, ustaw klucz i binduj host:
```bat
set 321_AI_API_KEY=ustaw_dlugi_losowy_klucz
321 ai serve "C:\sciezka\do\modelu" --host 0.0.0.0 --port 8000
```
Klient wysyła `Authorization: Bearer TWÓJ_KLUCZ`. Serwer odmawia startu poza localhost bez klucza. Nie wystawiaj portu publicznie bez TLS, zapory, limitów żądań i reverse proxy. API nie obsługuje jeszcze streamingu ani generowania obrazów.

## Publikowanie modelu na Hugging Face
Ustaw `HF_TOKEN` jako zmienną środowiskową (nie zapisuj go w repo ani config.json):
```bat
set HF_TOKEN=hf_...
321 ai publish-hf "C:\sciezka\do\modelu" --repo-id TWOJE_KONTO/NAZWA_MODELU
```
Domyślnie repozytorium jest prywatne; `--public` zmienia widoczność. Publikowane są wagi, konfiguracja i README. Przed publikacją dodaj wymagane atrybucje datasetów i sprawdź warunki licencji.

## Oryginalny model obrazowy 321 AI
To odrębna, eksperymentalna architektura DDPM/U-Net napisana w projekcie i trenowana od zera — bez gotowego zewnętrznego generatora. Obecna wersja jest bezwarunkowa, generuje 64×64 i nie przyjmuje promptu tekstowego. Używaj wyłącznie lokalnych obrazów, do których masz prawa:
```bat
321 ai train-images "C:\legalne_obrazy" --output "C:\modele\321-image" --steps 20000 --batch 16
321 ai generate-image "C:\modele\321-image" --count 1 --output "C:\wygenerowane"
```
Checkpoint: `image_model.pt`. Jakość może być niska przy małym zbiorze lub krótkim treningu; pipeline nie jest jeszcze częścią tekstowego API.

## Ograniczenia
- Model tekstowy to eksperymentalny byte-level Transformer trenowany od zera, nie model foundation/pretrained.
- Model obrazowy to unconditional DDPM 64×64, nie generator prompt-to-image.
- Brak gwarancji jakości. Wynik zależy od legalności, jakości, różnorodności i skali danych, treningu oraz sprzętu.
- Checkpointy mogą zajmować dużo miejsca — rób kopie zapasowe.
- CI sprawdza składnię i testy bez GPU; nie potwierdza długiego treningu ani wdrożenia produkcyjnego.
