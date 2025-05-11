import requests
import os
from dotenv import load_dotenv
import logging
import re
import jsonschema
import json

# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = os.getenv('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent')

# Logger do pliku app.log
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
def log_event(msg):
    logging.info(msg)

# Funkcja do wysyłania tekstu do Gemini 2.0 Flash Lite
# Dokumentacja: https://ai.google.dev/api/rest/v1beta/models/generateContent

def extract_products_from_receipt(text, sklep):
    """
    Wysyła tekst paragonu do Gemini 2.0 Flash Lite i zwraca ustrukturyzowane dane o produktach.
    Uwzględnia wybrany sklep i szczegółowe instrukcje rozpoznawania.
    """
    if not GEMINI_API_KEY:
        raise Exception("Brak klucza GEMINI_API_KEY w pliku .env!")
    prompt = f"""
    Odczytaj z poniższego tekstu paragonu listę produktów, ich ilości, ceny jednostkowe, rabaty, jednostki miary, sklep, datę zakupu.
    Sklep: {sklep}
    Uwzględnij specyfikę sklepu (Lidl, Kaufland, Biedronka):
    - Rozpoznawaj kody promocji, kategorie podatkowe, produkty wagowe.
    - Normalizuj nazwy produktów (np. 'PomKroNaszSpiz240g' → 'Pomidory krojone w sosie własnym 240g').
    - Przypisz kategorię na podstawie nazwy i stawki podatkowej.
    - Wyodrębnij ilość i jednostkę miary z różnych formatów (np. 2×1,79; 0.365 × 3,69).
    - Oznacz rabaty i promocje.
    - Dla każdej pozycji podaj ocenę pewności rozpoznania (0-100%).
    Zwróć dane w formacie JSON:
    [
      {{
        "produkt": "...",
        "nazwa_znormalizowana": "...",
        "kategoria": "...",
        "ilosc": ...,
        "jednostka": "...",
        "cena_jednostkowa": ...,
        "cena_laczna": ...,
        "data_waznosci": "...",
        "data_zakupu": "...",
        "sklep": "...",
        "zamrozony": false,
        "rabat": ...,
        "kategoria_podatkowa": "...",
        "status": "dostępny",
        "pewnosc": 95
      }}
    ]
    Tekst paragonu:
    {text}
    """
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=data)
    logging.debug(f"[LLM] Pełna odpowiedź Gemini: {response.text}")
    log_event(f"[LLM] Pełna odpowiedź Gemini: {response.text}")
    if response.status_code == 200:
        try:
            candidates = response.json().get('candidates', [])
            if candidates:
                text_response = candidates[0]['content']['parts'][0]['text']
                # Usuwanie bloków ```json ... ```
                text_response = re.sub(r'^```json\s*', '', text_response.strip(), flags=re.MULTILINE)
                text_response = re.sub(r'```$', '', text_response.strip(), flags=re.MULTILINE)
                text_response = text_response.strip()
                # Próba naprawy typowych błędów JSON
                text_response = re.sub(r',\s*([}\]])', r'\1', text_response)  # usuwanie przecinków przed zamknięciem
                text_response = text_response.replace("'", '"')  # pojedyncze na podwójne cudzysłowy
                # Parsowanie JSON
                try:
                    products = json.loads(text_response)
                except Exception as e:
                    log_event(f"[LLM] Błąd parsowania JSON: {e} | Odpowiedź: {text_response}")
                    raise Exception(f"Błąd parsowania odpowiedzi Gemini: {e}")
                # Walidacja schematu
                schema = {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "produkt": {"type": "string"},
                            "nazwa_znormalizowana": {"type": "string"},
                            "kategoria": {"type": "string"},
                            "ilosc": {"type": ["number", "integer"]},
                            "jednostka": {"type": "string"},
                            "cena_jednostkowa": {"type": ["number", "integer"]},
                            "cena_laczna": {"type": ["number", "integer"]},
                            "data_waznosci": {"type": ["string", "null"]},
                            "data_zakupu": {"type": ["string", "null"]},
                            "sklep": {"type": "string"},
                            "zamrozony": {"type": ["boolean", "integer"]},
                            "rabat": {"type": ["number", "integer"]},
                            "kategoria_podatkowa": {"type": ["string", "null"]},
                            "status": {"type": "string"},
                            "pewnosc": {"type": ["number", "integer"]}
                        },
                        "required": ["produkt", "nazwa_znormalizowana", "kategoria", "ilosc", "jednostka", "cena_jednostkowa", "cena_laczna", "sklep", "status", "pewnosc"]
                    }
                }
                try:
                    jsonschema.validate(products, schema)
                except Exception as e:
                    log_event(f"[LLM] Błąd walidacji schematu: {e} | Dane: {products}")
                    raise Exception(f"Błąd walidacji odpowiedzi Gemini: {e}")
                # Uzupełnianie brakującej daty zakupu
                from datetime import datetime
                for prod in products:
                    if not prod.get('data_zakupu') or prod.get('data_zakupu') in [None, '', 'null']:
                        prod['data_zakupu'] = datetime.now().strftime('%Y-%m-%d')
                    if not prod.get('data_waznosci') or prod.get('data_waznosci') in [None, '', 'null']:
                        prod['data_waznosci'] = None
                return products
            else:
                log_event("[LLM] Brak kandydatów w odpowiedzi Gemini.")
                raise Exception("Brak odpowiedzi z modelu Gemini.")
        except Exception as e:
            log_event(f"[LLM] Błąd przetwarzania odpowiedzi Gemini: {e} | Odpowiedź: {response.text}")
            raise Exception(f"Błąd przetwarzania odpowiedzi Gemini: {e}")
    else:
        log_event(f"[LLM] Błąd Gemini: {response.status_code} {response.text}")
        raise Exception(f"Błąd Gemini: {response.status_code} {response.text}") 