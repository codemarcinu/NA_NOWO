# Aplikacja do zarządzania zakupami i zapasami spożywczymi

## Opis
Prosta aplikacja webowa (działająca lokalnie), która pomaga rejestrować zakupy spożywcze na podstawie elektronicznych paragonów (PDF/JPG/PNG), zarządzać zapasami w domu, planować posiłki i analizować wydatki. Wszystko w języku polskim, bez logowania.

## Główne funkcje
- Rejestracja zakupów na podstawie paragonów (OCR + LLM Gemini 2.0 Flash Lite)
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
4. (Opcjonalnie) Zainstaluj pdf2image, jeśli chcesz obsługiwać PDF:
   ```bash
   pip install pdf2image
   sudo apt install poppler-utils
   ```
5. Skonfiguruj klucz API Gemini (patrz niżej).
6. Uruchom aplikację:
   ```bash
   streamlit run app.py
   ```
7. W przeglądarce pojawi się menu z modułami:
   - **Dashboard**: szybkie podsumowanie zapasów i wydatków.
   - **Dodaj paragon (OCR)**: wgraj plik, wybierz sklep, przetwórz OCR. Paragon trafi do kolejki oczekujących.
   - **Paragony oczekujące na przetworzenie**: popraw tekst OCR, wyślij do LLM, edytuj produkty i zapisz do bazy. **Dopiero tutaj produkty trafiają do bazy danych!**
   - **Lista produktów**: przeglądaj, edytuj, usuwaj produkty, filtruj po statusie, sklepie, kategorii, pewności.
   - **Planowanie posiłków**: wybierz produkty do zużycia, ilość zostanie odjęta z bazy.
   - **Analityka wydatków**: wykresy, kalendarz zakupów, sumy wg sklepów/kategorii.
   - **Lista zakupów**: automatyczna lista na podstawie braków i dat ważności.
   - **Ustawienia**: konfiguracja klucza API i innych opcji.

**Podgląd plików:**
- Po wgraniu obrazu lub PDF możesz kliknąć "Powiększ podgląd..." pod miniaturą, aby zobaczyć plik w większym rozmiarze.
- Funkcja działa w sekcjach: Dodaj paragon, Paragony oczekujące na przetworzenie, Rejestracja paragonu.

**Jak działa rejestracja paragonu?**
1. Wgraj plik w sekcji **Dodaj paragon (OCR)** i wybierz sklep.
2. Paragon trafi do sekcji **Paragony oczekujące na przetworzenie**.
3. Tam możesz poprawić tekst OCR, wysłać do LLM, edytować produkty i **dopiero po zatwierdzeniu produkty zostaną zapisane do bazy**.
4. Dzięki temu masz pełną kontrolę nad tym, co trafia do bazy danych.

## Konfiguracja modelu Gemini (LLM)
1. Skopiuj plik `.env.example` do `.env`:
   ```bash
   cp .env.example .env
   ```
2. W pliku `.env` wpisz swój klucz API do Gemini:
   ```env
   GEMINI_API_KEY=tu_wstaw_swoj_klucz_api
   GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent
   ```
3. Klucz API będzie automatycznie używany przez aplikację. Nie musisz go wpisywać ręcznie.

## Uruchomienie
1. W terminalu wpisz:
   ```bash
   streamlit run app.py
   ```
2. Otworzy się przeglądarka z aplikacją.

## Struktura projektu
- `app.py` – główny plik aplikacji
- `ocr/` – moduł OCR
- `llm/` – integracja z LLM Gemini
- `db/` – obsługa bazy danych
- `static/` – pliki statyczne (np. przykładowe paragony)
- `.env.example` – wzór pliku z kluczem API

## Przykładowe rozszerzenia
- Eksport danych do Excela
- Wersja mobilna
- Synchronizacja z chmurą
- Rozbudowana analityka

---

Aplikacja jest w pełni lokalna, prosta w obsłudze i gotowa do rozbudowy. 