import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
import logging

DB_PATH = 'produkty.db'

def init_db():
    """
    Tworzy bazę danych i tabele, jeśli nie istnieją. Dodaje brakujące kolumny i indeksy.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            # Tabela produktów
            conn.execute('''
                CREATE TABLE IF NOT EXISTS produkty (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nazwa TEXT,
                    nazwa_znormalizowana TEXT,
                    ilosc REAL,
                    jednostka TEXT,
                    kategoria TEXT,
                    data_waznosci TEXT,
                    sklep TEXT,
                    cena_jednostkowa REAL,
                    cena_laczna REAL,
                    rabat REAL,
                    data_zakupu TEXT,
                    status TEXT,
                    kategoria_podatkowa TEXT,
                    zamrozony INTEGER,
                    pewnosc INTEGER
                )
            ''')
            # Dodaj brakującą kolumnę nazwa_znormalizowana, jeśli nie istnieje
            try:
                conn.execute("SELECT nazwa_znormalizowana FROM produkty LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE produkty ADD COLUMN nazwa_znormalizowana TEXT")
                print("Dodano brakującą kolumnę 'nazwa_znormalizowana'")
            # Dodaj indeksy na najczęściej wyszukiwane kolumny
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_nazwa ON produkty(nazwa)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_nazwa_znormalizowana ON produkty(nazwa_znormalizowana)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_kategoria ON produkty(kategoria)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_data_waznosci ON produkty(data_waznosci)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_sklep ON produkty(sklep)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_data_zakupu ON produkty(data_zakupu)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_produkty_status ON produkty(status)')
            # Tabela paragonów oczekujących
            conn.execute('''
                CREATE TABLE IF NOT EXISTS paragony_oczekujace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nazwa_pliku TEXT,
                    sciezka TEXT,
                    sklep TEXT,
                    tekst_ocr TEXT,
                    data_dodania TEXT
                )
            ''')
            # Indeksy dla paragonów
            conn.execute('CREATE INDEX IF NOT EXISTS idx_paragony_sklep ON paragony_oczekujace(sklep)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_paragony_data_dodania ON paragony_oczekujace(data_dodania)')

def normalize_date(date_str):
    """Próbuje znormalizować datę do formatu YYYY-MM-DD."""
    if not date_str:
        return None
    formats = [
        '%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y', '%Y.%m.%d', '%Y/%m/%d'
    ]
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def validate_product(product):
    """
    Waliduje dane produktu przed zapisem do bazy.
    Sprawdza wymagane pola, typy, daty, liczby, normalizuje daty.
    Zwraca listę błędów (jeśli pusta, produkt jest OK).
    """
    errors = []
    # Wymagane pola
    required_fields = ['nazwa', 'ilosc', 'kategoria', 'sklep', 'data_zakupu']
    for field in required_fields:
        if field not in product or not product[field]:
            errors.append(f"Brak wymaganego pola: {field}")
    # Typy liczbowe
    for field in ['ilosc', 'cena_jednostkowa', 'cena_laczna', 'rabat']:
        if field in product and product[field] is not None:
            try:
                product[field] = float(product[field])
                if product[field] < 0:
                    errors.append(f"Wartość dla pola '{field}' nie może być ujemna: {product[field]}")
            except (ValueError, TypeError):
                errors.append(f"Niepoprawna wartość dla pola '{field}': {product[field]}")
    # Normalizacja i walidacja dat
    if 'data_zakupu' in product and product['data_zakupu']:
        normalized = normalize_date(product['data_zakupu'])
        if normalized:
            product['data_zakupu'] = normalized
        else:
            errors.append(f"Niepoprawny format daty zakupu: {product['data_zakupu']}")
    if 'data_waznosci' in product and product['data_waznosci']:
        normalized = normalize_date(product['data_waznosci'])
        if normalized:
            product['data_waznosci'] = normalized
        else:
            errors.append(f"Niepoprawny format daty ważności: {product['data_waznosci']}")
    # Data ważności nie może być wcześniejsza niż data zakupu
    if product.get('data_zakupu') and product.get('data_waznosci'):
        try:
            if product['data_waznosci'] < product['data_zakupu']:
                errors.append("Data ważności nie może być wcześniejsza niż data zakupu")
        except:
            pass
    return errors

def add_product(prod):
    """
    Dodaje produkt do bazy danych po walidacji.
    prod: słownik z danymi produktu
    """
    # Walidacja danych
    errors = validate_product(prod)
    if errors:
        error_msg = "; ".join(errors)
        logging.error(f"[ZAPIS][BŁĄD] Błędy walidacji: {error_msg}")
        raise ValueError(f"Błędy walidacji: {error_msg}")
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                INSERT INTO produkty (nazwa, nazwa_znormalizowana, ilosc, jednostka, kategoria, data_waznosci, sklep, cena_jednostkowa, cena_laczna, rabat, data_zakupu, status, kategoria_podatkowa, zamrozony, pewnosc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prod.get('nazwa'),
                prod.get('nazwa_znormalizowana'),
                prod.get('ilosc'),
                prod.get('jednostka'),
                prod.get('kategoria'),
                prod.get('data_waznosci'),
                prod.get('sklep'),
                prod.get('cena_jednostkowa'),
                prod.get('cena_laczna'),
                prod.get('rabat'),
                prod.get('data_zakupu'),
                prod.get('status'),
                prod.get('kategoria_podatkowa'),
                int(prod.get('zamrozony', 0)),
                prod.get('pewnosc')
            ))

def get_products():
    """
    Zwraca listę wszystkich produktów z bazy.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM produkty')
        return cur.fetchall()

def update_product(prod_id, prod):
    """
    Aktualizuje dane produktu o podanym id.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                UPDATE produkty SET nazwa=?, nazwa_znormalizowana=?, ilosc=?, jednostka=?, kategoria=?, data_waznosci=?, sklep=?, cena_jednostkowa=?, cena_laczna=?, rabat=?, data_zakupu=?, status=?, kategoria_podatkowa=?, zamrozony=?, pewnosc=?
                WHERE id=?
            ''', (
                prod.get('nazwa'),
                prod.get('nazwa_znormalizowana'),
                prod.get('ilosc'),
                prod.get('jednostka'),
                prod.get('kategoria'),
                prod.get('data_waznosci'),
                prod.get('sklep'),
                prod.get('cena_jednostkowa'),
                prod.get('cena_laczna'),
                prod.get('rabat'),
                prod.get('data_zakupu'),
                prod.get('status'),
                prod.get('kategoria_podatkowa'),
                int(prod.get('zamrozony', 0)),
                prod.get('pewnosc'),
                prod_id
            ))

def delete_product(prod_id):
    """
    Usuwa produkt o podanym id.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('DELETE FROM produkty WHERE id=?', (prod_id,))

def add_pending_receipt(nazwa_pliku, sciezka, sklep, tekst_ocr):
    """Dodaje paragon do tabeli oczekujących."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                INSERT INTO paragony_oczekujace (nazwa_pliku, sciezka, sklep, tekst_ocr, data_dodania)
                VALUES (?, ?, ?, ?, ?)
            ''', (nazwa_pliku, sciezka, sklep, tekst_ocr, datetime.now().isoformat()))

def get_pending_receipts():
    """Zwraca listę wszystkich oczekujących paragonów."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM paragony_oczekujace')
        return cur.fetchall()

def delete_pending_receipt(receipt_id):
    """Usuwa oczekujący paragon o podanym id."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('DELETE FROM paragony_oczekujace WHERE id=?', (receipt_id,))

def count_all_products():
    """
    Zwraca liczbę wszystkich produktów w bazie.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM produkty')
        return cur.fetchone()[0]

def count_expired_products():
    """
    Zwraca liczbę produktów, których data ważności minęła (przeterminowane).
    """
    today = datetime.now().date()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM produkty WHERE data_waznosci IS NOT NULL AND date(data_waznosci) < ?', (today.isoformat(),))
        return cur.fetchone()[0]

def sum_expenses_current_month():
    """
    Zwraca sumę wydatków (cena_laczna) z bieżącego miesiąca.
    """
    today = datetime.now()
    first_day = today.replace(day=1).date().isoformat()
    last_day = today.date().isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute('''SELECT SUM(cena_laczna) FROM produkty WHERE data_zakupu IS NOT NULL AND date(data_zakupu) >= ? AND date(data_zakupu) <= ?''', (first_day, last_day))
        result = cur.fetchone()[0]
        return result if result else 0

def count_expiring_soon_products(days=3):
    """
    Zwraca liczbę produktów, którym kończy się ważność w najbliższych X dniach (domyślnie 3).
    """
    today = datetime.now().date()
    soon = today + timedelta(days=days)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute('''SELECT COUNT(*) FROM produkty WHERE data_waznosci IS NOT NULL AND date(data_waznosci) >= ? AND date(data_waznosci) <= ?''', (today.isoformat(), soon.isoformat()))
        return cur.fetchone()[0] 