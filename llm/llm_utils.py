import os
import json
import logging
from dotenv import load_dotenv

# Nowe importy
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
import requests
import re
import jsonschema

# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()
LLM_TYPE = os.getenv('LLM_TYPE', 'local')
LOCAL_LLM_URL = os.getenv('LOCAL_LLM_URL', 'http://192.168.0.167:1234/v1')
LOCAL_LLM_MODEL = os.getenv('LOCAL_LLM_MODEL', 'bielik-4.5b-v3.0-instruct')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = os.getenv('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent')

# Logger do pliku app.log
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
def log_event(msg):
    logging.info(msg)

# Funkcja do wysyłania tekstu do Gemini 2.0 Flash Lite
# Dokumentacja: https://ai.google.dev/api/rest/v1beta/models/generateContent

def extract_products_from_receipt(text, shop=None):
    """
    Wysyła tekst paragonu do wybranego modelu LLM (lokalny Bielik lub Gemini) i zwraca listę produktów.
    Rabaty, kupony, zniżki, upusty NIE są produktami i nie mogą być zwracane jako osobne produkty.
    Rabat należy przypisać do produktu, jeśli występuje.
    """
    def filter_out_discounts(products):
        # Filtruje produkty, których nazwa sugeruje rabat, kupon, zniżkę, upust, promocję
        blacklist = ["rabat", "kupon", "zniżka", "upust", "promocja", "voucher", "bon", "obniżka", "zniż", "discount", "coupon"]
        filtered = []
        for prod in products:
            nazwa = (prod.get("nazwa_znormalizowana") or prod.get("produkt") or "").lower()
            if not any(word in nazwa for word in blacklist):
                filtered.append(prod)
        return filtered
    if LLM_TYPE == 'local':
        if OpenAI is None:
            raise ImportError("openai nie jest zainstalowane. Dodaj 'openai' do requirements.txt i zainstaluj.")
        try:
            client = OpenAI(
                base_url=LOCAL_LLM_URL,
                api_key="not-needed"
            )
            system_prompt = """
            Przeanalizuj poniższy tekst z paragonu sklepowego i zwróć listę produktów w formacie JSON.
            Dla każdego produktu wyodrębnij: nazwę (tak jak na paragonie), znormalizowaną nazwę (bardziej czytelną),
            ilość, jednostkę, kategorię produktu, cenę jednostkową, cenę łączną, rabat (jeśli jest).
            RABAT, KUPON, ZNIŻKA, UPUST, PROMOCJA NIE SĄ PRODUKTAMI i nie mogą być zwracane jako osobne produkty. Rabat należy przypisać do produktu, jeśli występuje.
            Format odpowiedzi powinien być tablicą obiektów JSON, każdy obiekt z polami:
            {
                "nazwa": "nazwa z paragonu",
                "nazwa_znormalizowana": "czytelna nazwa",
                "ilosc": liczba,
                "jednostka": "szt./kg/l/g/itd.",
                "kategoria": "Mleko i produkty mleczne/Mięso i wędliny/Warzywa i owoce/Pieczywo/itd.",
                "cena_jednostkowa": liczba,
                "cena_laczna": liczba,
                "rabat": liczba,
                "sklep": "nazwa sklepu",
                "data_zakupu": "dzisiejsza data",
                "status": "dostępny",
                "kategoria_podatkowa": "A/B/C/D/E",
                "zamrozony": false,
                "pewnosc": liczba od 0 do 1
            }
            NIE ZWRACAJ rabatów, kuponów, zniżek, upustów, promocji jako osobnych produktów!
            """
            if shop:
                system_prompt += f"\nParagon jest ze sklepu: {shop}."
            response = client.chat.completions.create(
                model=LOCAL_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.2
            )
            response_text = response.choices[0].message.content
            # Szukamy JSON w odpowiedzi
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                products_json = json_match.group(1)
            else:
                products_json = response_text
            products = json.loads(products_json)
            # Uzupełnianie brakujących pól
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            for product in products:
                if "data_zakupu" not in product:
                    product["data_zakupu"] = current_date
                if "sklep" not in product:
                    product["sklep"] = shop or "Nieznany"
                if "status" not in product:
                    product["status"] = "dostępny"
                if "zamrozony" not in product:
                    product["zamrozony"] = False
                if "pewnosc" not in product:
                    product["pewnosc"] = 0.8
            return filter_out_discounts(products)
        except Exception as e:
            log_event(f"[LLM] Błąd lokalnego LLM: {e}")
            return []
    else:
        # --- GEMINI API (jak dotychczas) ---
        if not GEMINI_API_KEY:
            raise Exception("Brak klucza GEMINI_API_KEY w pliku .env!")
        prompt = f"""
        Odczytaj z poniższego tekstu paragonu listę produktów, ich ilości, ceny jednostkowe, rabaty, jednostki miary, sklep, datę zakupu.
        Sklep: {shop}
        UWAGA: Rabaty, kupony, zniżki, upusty, promocje NIE są produktami i nie mogą być zwracane jako osobne produkty. Rabat należy przypisać do produktu, jeśli występuje.
        Uwzględnij specyfikę sklepu (Lidl, Kaufland, Biedronka):
        - Rozpoznawaj kody promocji, kategorie podatkowe, produkty wagowe.
        - Normalizuj nazwy produktów (np. 'PomKroNaszSpiz240g' → 'Pomidory krojone w sosie własnym 240g').
        - Przypisz kategorię na podstawie nazwy i stawki podatkowej.
        - Wyodrębnij ilość i jednostkę miary z różnych formatów (np. 2×1,79; 0.365 × 3,69).
        - Oznacz rabaty i promocje.
        - Dla każdej pozycji podaj ocenę pewności rozpoznania (0-100%).
        NIE ZWRACAJ rabatów, kuponów, zniżek, upustów, promocji jako osobnych produktów!
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
        log_event(f"[LLM] Pełna odpowiedź Gemini: {response.text}")
        if response.status_code == 200:
            try:
                candidates = response.json().get('candidates', [])
                if candidates:
                    text_response = candidates[0]['content']['parts'][0]['text']
                    text_response = re.sub(r'^```json\s*', '', text_response.strip(), flags=re.MULTILINE)
                    text_response = re.sub(r'```$', '', text_response.strip(), flags=re.MULTILINE)
                    text_response = text_response.strip()
                    text_response = re.sub(r',\s*([}\]])', r'\1', text_response)
                    text_response = text_response.replace("'", '"')
                    products = json.loads(text_response)
                    from datetime import datetime
                    for prod in products:
                        if not prod.get('data_zakupu') or prod.get('data_zakupu') in [None, '', 'null']:
                            prod['data_zakupu'] = datetime.now().strftime('%Y-%m-%d')
                        if not prod.get('data_waznosci') or prod.get('data_waznosci') in [None, '', 'null']:
                            prod['data_waznosci'] = None
                    return filter_out_discounts(products)
                else:
                    log_event("[LLM] Brak kandydatów w odpowiedzi Gemini.")
                    return []
            except Exception as e:
                log_event(f"[LLM] Błąd przetwarzania odpowiedzi Gemini: {e} | Odpowiedź: {response.text}")
                return []
        else:
            log_event(f"[LLM] Błąd Gemini: {response.status_code} {response.text}")
            return []

# Walidacja schematu
def validate_schema(products):
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