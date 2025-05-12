import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

DB_PATH = 'produkty.db'

def init_db():
    """
    Tworzy bazę danych i tabele, jeśli nie istnieją.
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

def add_product(prod):
    """
    Dodaje produkt do bazy danych.
    prod: słownik z danymi produktu
    """
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