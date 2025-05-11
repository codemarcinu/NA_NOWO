import sqlite3
from contextlib import closing
from datetime import datetime

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