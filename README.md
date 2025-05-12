# Aplikacja do zarządzania zakupami i zapasami spożywczymi

## Opis
Prosta aplikacja webowa (działająca lokalnie), która pomaga rejestrować zakupy spożywcze na podstawie elektronicznych paragonów (PDF/JPG/PNG), zarządzać zapasami w domu, planować posiłki i analizować wydatki. Wszystko w języku polskim, bez logowania.

## Główne funkcje
- Rejestracja zakupów na podstawie paragonów (OCR + LLM Gemini 2.0 Flash Lite lub lokalny Bielik)
- Kategoryzacja i podgląd produktów (ilości, daty ważności, kategorie)
- Planowanie posiłków i "zużywanie" produktów
- Prosta analityka wydatków (kalendarz, wykresy)
- Edycja i usuwanie produktów
- Podgląd plików (obrazów i PDF) z możliwością powiększenia po kliknięciu
- Kolejka paragonów oczekujących na przetworzenie (możliwość poprawy tekstu OCR przed analizą LLM)
- Automatyczna lista zakupów na podstawie braków i dat ważności
- Alerty o kończących się/przeterminowanych produktach
- Logowanie zdarzeń do pliku `app.log`

## Wymagania
- Python 3.11 lub nowszy
- System Linux (np. Linux Mint)
- Tesseract OCR (`sudo apt install tesseract-ocr`)
- (Opcjonalnie) Poppler do PDF (`sudo apt install poppler-utils`)
- (Opcjonalnie) LM Studio do lokalnego modelu Bielik

## Instrukcja obsługi (krok po kroku)
1. Otwórz terminal i przejdź do folderu z aplikacją.
2. Zainstaluj wymagane biblioteki:
   ```bash
   pip install -r requirements.txt
   ```
3. Zainstaluj Tesseract OCR (jeśli nie masz):
   ```bash
   sudo apt update
   sudo apt install tesseract-ocr
   ```
4. (Opcjonalnie) Zainstaluj pdf2image i poppler-utils, jeśli chcesz obsługiwać PDF:
   ```bash
   pip install pdf2image
   sudo apt install poppler-utils
   ```
5. (Opcjonalnie) Skonfiguruj lokalny model Bielik w LM Studio:
   - Pobierz model Bielik-4.5b-v3.0-instruct i uruchom LM Studio z API OpenAI na porcie 1234.
   - W aplikacji przejdź do **Ustawienia** i wybierz "Lokalny (Bielik)".
   - Sprawdź połączenie z modelem.
6. (Alternatywnie) Skonfiguruj klucz API Gemini (patrz niżej).
7. Uruchom aplikację:
   ```bash
   streamlit run app.py
   ```
8. W przeglądarce pojawi się menu z modułami:
   - **Dashboard**: szybkie podsumowanie zapasów i wydatków.
   - **Dodaj paragon (OCR)**: wgraj plik, wybierz sklep, przetwórz OCR. Paragon trafi do kolejki oczekujących.
   - **Paragony oczekujące na przetworzenie**: popraw tekst OCR, wyślij do LLM, edytuj produkty i zapisz do bazy. **Dopiero tutaj produkty trafiają do bazy danych!**
   - **Lista produktów**: przeglądaj, edytuj, usuwaj produkty, filtruj po statusie, sklepie, kategorii, pewności.
   - **Planowanie posiłków**: wybierz produkty do zużycia, ilość zostanie odjęta z bazy.
   - **Analityka wydatków**: wykresy, kalendarz zakupów, sumy wg sklepów/kategorii.
   - **Lista zakupów**: automatyczna lista na podstawie braków i dat ważności.
   - **Ustawienia**: konfiguracja modelu LLM, klucza API i innych opcji.

**Podgląd plików:**
- Po wgraniu obrazu lub PDF możesz kliknąć "Powiększ podgląd..." pod miniaturą, aby zobaczyć plik w większym rozmiarze.
- Funkcja działa w sekcjach: Dodaj paragon, Paragony oczekujące na przetworzenie, Rejestracja paragonu.

**Jak działa rejestracja paragonu?**
1. Wgraj plik w sekcji **Dodaj paragon (OCR)** i wybierz sklep.
2. Paragon trafi do sekcji **Paragony oczekujące na przetworzenie**.
3. Tam możesz poprawić tekst OCR, wysłać do LLM, edytować produkty i **dopiero po zatwierdzeniu produkty zostaną zapisane do bazy**.
4. Dzięki temu masz pełną kontrolę nad tym, co trafia do bazy danych.

## Konfiguracja modelu LLM (Bielik lub Gemini)
1. Przejdź do sekcji **Ustawienia** w aplikacji.
2. Wybierz model: "Lokalny (Bielik)" lub "Gemini API".
3. Dla lokalnego modelu podaj adres i nazwę modelu (domyślnie: `http://localhost:1234/v1`, `bielik-4.5b-v3.0-instruct`).
4. Dla Gemini podaj klucz API i adres endpointu.
5. Zapisz ustawienia i sprawdź połączenie.

## Uruchomienie
1. W terminalu wpisz:
   ```bash
   streamlit run app.py
   ```
2. Otworzy się przeglądarka z aplikacją.

## Struktura projektu
- `app.py` – główny plik aplikacji
- `ocr/` – moduł OCR
- `llm/` – integracja z LLM (Bielik/Gemini)
- `db/` – obsługa bazy danych
- `custom_theme.css` – styl aplikacji
- `requirements.txt` – zależności
- `.env` – konfiguracja kluczy/modeli
- `produkty.db` – baza SQLite
- `app.log` – logi aplikacji

## Co jeszcze do dokończenia? (TODO)
- [ ] Dashboard: dynamiczne metryki i alerty na podstawie realnych danych
- [ ] Lista produktów: wyświetlanie, filtrowanie, edycja, usuwanie, paginacja
- [ ] Planowanie posiłków: wybór produktów, aktualizacja ilości, historia
- [ ] Analityka wydatków: wykresy, statystyki, eksport
- [ ] Lista zakupów: generowanie, edycja, eksport/drukowanie
- [ ] Walidacja danych produktu przed zapisem
- [ ] Lepsza obsługa błędów (OCR, LLM, baza)
- [ ] Reset bazy danych z potwierdzeniem/backupem
- [ ] Tryb debugowania/logi w aplikacji
- [ ] Responsywność i UX na urządzeniach mobilnych
- [ ] Onboarding dla nowych użytkowników
- [ ] Przykładowe dane do testów
- [ ] Pełna polska lokalizacja komunikatów

## Zgłaszanie błędów i sugestii
- Jeśli napotkasz błąd lub masz pomysł na usprawnienie, zgłoś go przez GitHub Issues lub mailowo do autora.
- W logu `app.log` znajdziesz szczegóły techniczne błędów.

## Onboarding (pierwsze uruchomienie)
1. Po uruchomieniu aplikacji przejdź do **Ustawienia** i wybierz model LLM.
2. Wgraj przykładowy paragon w sekcji **Dodaj paragon (OCR)**.
3. Przetestuj analizę LLM i edycję produktów.
4. Przeglądaj produkty, planuj posiłki, analizuj wydatki!

---
Aplikacja jest w pełni lokalna, prosta w obsłudze i gotowa do rozbudowy. 