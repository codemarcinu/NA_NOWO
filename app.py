import streamlit as st
import tempfile
import os
from ocr.ocr_utils import ocr_file
from llm.llm_utils import extract_products_from_receipt
from db.db_utils import (add_product, init_db, get_products, update_product, 
                        delete_product, add_pending_receipt, get_pending_receipts, 
                        delete_pending_receipt)
import pandas as pd
from datetime import datetime, timedelta
import logging
from PIL import Image
import re
import dotenv
import pathlib
import json
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

# Inicjalizacja bazy danych
init_db()

# Konfiguracja loggera
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
def log_event(msg):
    logging.info(msg)
    if st.session_state.get('debug_mode', False):
        st.write(f"[LOG] {msg}")

# Ustawienia strony
st.set_page_config(
    page_title="🛒 Zarządzanie zakupami i zapasami spożywczymi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. Ładowanie CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("custom_theme.css")

# --- 2. Implementacja funkcji render_dashboard ---
def render_dashboard():
    st.title("Dashboard")
    st.markdown("### Szybkie podsumowanie")
    
    # Przykładowe karty metryczne
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="card metric">
            <i class="material-icons">inventory_2</i>
            <div>
                <div>Produkty w zapasie</div>
                <h2>34</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card metric">
            <i class="material-icons">watch_later</i>
            <div>
                <div>Produkty przeterminowane</div>
                <h2>3</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card metric">
            <i class="material-icons">payments</i>
            <div>
                <div>Wydatki w tym miesiącu</div>
                <h2>432 zł</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Alerty
    st.markdown("""
    <div class="alert warning">
        <i class="material-icons">warning</i>
        <div>3 produkty niedługo się przeterminują</div>
    </div>
    """, unsafe_allow_html=True)

# --- 3. Funkcja do dodawania paragonu ---
def render_add_receipt():
    st.title("Dodaj paragon (OCR)")
    
    # Formularz dodawania paragonu
    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Wybierz plik (JPG, PNG, PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])
        sklep = st.selectbox("Wybierz sklep", ["Biedronka", "Lidl", "Kaufland", "Auchan", "Inny"])
        submit_button = st.form_submit_button("Przetwórz OCR")
    
    if submit_button and uploaded_file:
        try:
            # Zapisz plik tymczasowo
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                file_path = tmp_file.name
            
            # Wykonaj OCR na pliku
            try:
                tekst_ocr = ocr_file(file_path)
                # Skróć tekst dla wyświetlenia
                tekst_display = tekst_ocr[:300] + "..." if len(tekst_ocr) > 300 else tekst_ocr
                
                # Zapisz paragon do oczekujących
                add_pending_receipt(uploaded_file.name, file_path, sklep, tekst_ocr)
                
                # Wyświetl podgląd i informację o sukcesie
                st.success(f"Plik został wgrany i przetworzony przez OCR. Przejdź do sekcji 'Paragony oczekujące' aby dokończyć proces.")
                
                # Podgląd pliku
                if uploaded_file.name.lower().endswith(('jpg', 'jpeg', 'png')):
                    image = Image.open(file_path)
                    st.image(image, caption=f"Podgląd: {uploaded_file.name}", width=400)
                elif uploaded_file.name.lower().endswith('pdf') and convert_from_path:
                    images = convert_from_path(file_path, first_page=1, last_page=1)
                    if images:
                        st.image(images[0], caption=f"Podgląd pierwszej strony: {uploaded_file.name}", width=400)
                
                # Podgląd tekstu OCR
                st.subheader("Rozpoznany tekst:")
                st.text_area("", value=tekst_display, height=200, disabled=True)
                
                log_event(f"Plik wgrany: {uploaded_file.name}")
                log_event(f"OCR OK dla pliku {uploaded_file.name}. Tekst: {tekst_ocr[:100]}...")
                
            except Exception as e:
                st.error(f"Błąd OCR: {str(e)}")
                log_event(f"Błąd OCR: {str(e)}")
                # Usuń plik tymczasowy
                try:
                    os.unlink(file_path)
                except:
                    pass
        except Exception as e:
            st.error(f"Błąd podczas przetwarzania pliku: {str(e)}")
            log_event(f"Błąd podczas przetwarzania pliku: {str(e)}")

# --- 4. Funkcja do przeglądania oczekujących paragonów ---
def render_pending_receipts():
    st.title("Paragony oczekujące na przetworzenie")
    
    # Pobierz paragony oczekujące
    receipts = get_pending_receipts()
    
    if not receipts:
        st.info("Brak paragonów oczekujących na przetworzenie.")
        return
    
    # Wyświetl listę paragonów
    for receipt in receipts:
        receipt_id, nazwa_pliku, sciezka, sklep, tekst_ocr, data_dodania = receipt
        
        st.markdown(f"""
        <div class="card">
            <h3>{nazwa_pliku}</h3>
            <p>Sklep: {sklep}</p>
            <p>Data dodania: {data_dodania}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Formularz do przetworzenia paragonu
        with st.expander(f"Przetwórz paragon #{receipt_id}"):
            # Podgląd pliku
            if os.path.exists(sciezka):
                if sciezka.lower().endswith(('jpg', 'jpeg', 'png')):
                    image = Image.open(sciezka)
                    st.image(image, caption=f"Podgląd: {nazwa_pliku}", width=400)
                elif sciezka.lower().endswith('pdf') and convert_from_path:
                    try:
                        images = convert_from_path(sciezka, first_page=1, last_page=1)
                        if images:
                            st.image(images[0], caption=f"Podgląd pierwszej strony: {nazwa_pliku}", width=400)
                    except Exception as e:
                        st.error(f"Błąd podglądu PDF: {str(e)}")
            
            # Edycja tekstu OCR
            edited_ocr = st.text_area(f"Edytuj tekst OCR", value=tekst_ocr, height=200)
            
            # Przyciski akcji
            if st.button("Analizuj LLM", key=f"analyze_{receipt_id}"):
                try:
                    st.info("Wysyłanie do analizy... To może potrwać chwilę.")
                    log_event(f"Prompt do LLM (sklep: {sklep}): {edited_ocr[:100]}...")
                    products = extract_products_from_receipt(edited_ocr, sklep)
                    
                    # Zapisz wyniki do session_state
                    key = f"products_{receipt_id}"
                    st.session_state[key] = products
                    
                    st.success(f"Analiza zakończona. Wykryto {len(products)} produktów.")
                    
                    # Wyświetl wyniki
                    for i, prod in enumerate(products):
                        with st.expander(f"Produkt #{i+1}: {prod.get('nazwa_znormalizowana', 'Brak nazwy')}"):
                            # Konwertuj dict na JSON, a następnie z powrotem aby zapewnić edytowalność
                            prod_json = json.dumps(prod, indent=2)
                            edited_prod_json = st.text_area(f"Edytuj dane produktu", value=prod_json, height=300, key=f"prod_{receipt_id}_{i}")
                            
                            try:
                                # Aktualizuj produkt w session_state
                                edited_prod = json.loads(edited_prod_json)
                                st.session_state[key][i] = edited_prod
                            except json.JSONDecodeError as e:
                                st.error(f"Błąd formatu JSON: {str(e)}")
                    
                    # Przycisk do zapisania wszystkich produktów
                    if st.button("Zapisz wszystkie produkty do bazy", key=f"save_all_{receipt_id}"):
                        for prod in st.session_state[key]:
                            try:
                                add_product(prod)
                                st.success(f"Dodano produkt: {prod.get('nazwa_znormalizowana', 'Brak nazwy')}")
                            except Exception as e:
                                st.error(f"Błąd dodawania produktu: {str(e)}")
                        
                        # Usuń paragon z oczekujących
                        delete_pending_receipt(receipt_id)
                        st.success("Wszystkie produkty zostały zapisane. Paragon został usunięty z oczekujących.")
                        st.experimental_rerun()
                
                except Exception as e:
                    st.error(f"Błąd analizy LLM: {str(e)}")
                    log_event(f"Błąd LLM: {str(e)}")
            
            # Przycisk do usunięcia paragonu
            if st.button("Usuń paragon", key=f"delete_{receipt_id}"):
                try:
                    delete_pending_receipt(receipt_id)
                    # Spróbuj usunąć plik tymczasowy
                    try:
                        if os.path.exists(sciezka):
                            os.unlink(sciezka)
                    except:
                        pass
                    st.success("Paragon został usunięty.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Błąd usuwania paragonu: {str(e)}")

# --- 5. Inne funkcje dla pozostałych widoków ---
def render_products_list():
    st.title("Lista produktów")
    st.info("Ten widok jest w trakcie implementacji.")

def render_meal_planning():
    st.title("Planowanie posiłków")
    st.info("Ten widok jest w trakcie implementacji.")

def render_analytics():
    st.title("Analityka wydatków")
    st.info("Ten widok jest w trakcie implementacji.")

def render_shopping_list():
    st.title("Lista zakupów")
    st.info("Ten widok jest w trakcie implementacji.")

def render_settings():
    st.title("Ustawienia")
    st.info("Ten widok jest w trakcie implementacji.")

# --- 6. Material Design CSS i ikony ---
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# --- 7. Przygotowanie menu ---
st.sidebar.title("Menu")

# Definiowanie opcji menu
menu_data = [
    {"icon": "dashboard", "label": "Dashboard", "id": "dashboard"},
    {"icon": "receipt", "label": "Dodaj paragon (OCR)", "id": "add_receipt"},
    {"icon": "pending", "label": "Paragony oczekujące", "id": "pending_receipts"},
    {"icon": "inventory_2", "label": "Lista produktów", "id": "products_list"},
    {"icon": "restaurant", "label": "Planowanie posiłków", "id": "meal_planning"},
    {"icon": "bar_chart", "label": "Analityka wydatków", "id": "analytics"},
    {"icon": "shopping_cart", "label": "Lista zakupów", "id": "shopping_list"},
    {"icon": "settings", "label": "Ustawienia", "id": "settings"}
]

# --- 8. Inicjalizacja stanu aplikacji ---
if 'page' not in st.session_state:
    st.session_state.page = "dashboard"

# --- 9. Funkcja zmiany strony ---
def change_page(page_id):
    st.session_state.page = page_id
    st.experimental_rerun()

# --- 10. Generowanie menu bocznego ---
for item in menu_data:
    # Określenie czy pozycja jest aktywna
    is_active = st.session_state.page == item["id"]
    menu_item_class = "active" if is_active else ""
    
    # Tworzenie przycisku menu
    if st.sidebar.button(
        f"{item['label']}",
        key=f"menu_{item['id']}",
        help=f"Przejdź do sekcji {item['label']}",
        on_click=change_page,
        args=(item["id"],)
    ):
        pass  # Przycisk automatycznie wywoła funkcję change_page

# --- 11. CSS do stylizacji przycisków menu ---
st.markdown("""
<style>
/* Ukrycie standardowych przycisków Streamlit w menu */
.sidebar button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: white !important;
    text-align: left !important;
    font-weight: normal !important;
    padding-left: 20px !important;
}

/* Dodanie ikon z Material Icons do przycisków */
.sidebar button:before {
    font-family: 'Material Icons';
    margin-right: 10px;
    vertical-align: middle;
    color: var(--accent);
}

.sidebar button[key="menu_dashboard"]:before { content: "dashboard"; }
.sidebar button[key="menu_add_receipt"]:before { content: "receipt"; }
.sidebar button[key="menu_pending_receipts"]:before { content: "pending"; }
.sidebar button[key="menu_products_list"]:before { content: "inventory_2"; }
.sidebar button[key="menu_meal_planning"]:before { content: "restaurant"; }
.sidebar button[key="menu_analytics"]:before { content: "bar_chart"; }
.sidebar button[key="menu_shopping_list"]:before { content: "shopping_cart"; }
.sidebar button[key="menu_settings"]:before { content: "settings"; }

/* Stylizacja aktywnego przycisku */
.sidebar button[aria-pressed="true"] {
    background: rgba(255,214,0,0.18) !important;
    border-left: 4px solid var(--accent) !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

# --- 12. Wyświetlanie odpowiedniej sekcji na podstawie session_state ---
if st.session_state.page == "dashboard":
    render_dashboard()
elif st.session_state.page == "add_receipt":
    render_add_receipt()
elif st.session_state.page == "pending_receipts":
    render_pending_receipts()
elif st.session_state.page == "products_list":
    render_products_list()
elif st.session_state.page == "meal_planning":
    render_meal_planning()
elif st.session_state.page == "analytics":
    render_analytics()
elif st.session_state.page == "shopping_list":
    render_shopping_list()
elif st.session_state.page == "settings":
    render_settings()
else:
    render_dashboard()