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
def log_event(msg):
    logging.info(msg)
    if st.session_state.get('debug_mode', False):
        st.write(f"[LOG] {msg}")
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

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

# --- 2. Przełącznik motywu (Material Design) ---
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
<div class="theme-toggle" id="theme-toggle" onclick="document.body.classList.toggle('dark'); 
     const icon = document.querySelector('#theme-toggle i');
     icon.textContent = document.body.classList.contains('dark') ? 'light_mode' : 'dark_mode';">
    <i class="material-icons">dark_mode</i>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    document.body.classList.add('dark');
});
</script>
""", unsafe_allow_html=True)

# --- 3. Definicja danych menu ---
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

# --- 4. Inicjalizacja session_state ---
if 'page' not in st.session_state:
    st.session_state.page = "dashboard"
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# --- 5. Funkcja do zmiany strony ---
def change_page(page_id):
    st.session_state.page = page_id
    st.experimental_rerun()

# --- 6. Generowanie menu bocznego ---
st.sidebar.markdown("<h3>Menu</h3>", unsafe_allow_html=True)

for item in menu_data:
    is_active = st.session_state.page == item["id"]
    menu_item_class = "menu-item active" if is_active else "menu-item"
    if st.sidebar.button(
        f"{item['label']}",
        key=f"menu_{item['id']}",
        help=f"Przejdź do sekcji {item['label']}",
        on_click=change_page,
        args=(item["id"],)
    ):
        pass
    st.sidebar.markdown(
        f"""<div id="icon-{item['id']}" class="menu-icon" style="display:none">
            <i class="material-icons">{item['icon']}</i>
        </div>""", 
        unsafe_allow_html=True
    )

# --- 7. CSS do zastąpienia przycisków Streamlit własnymi stylami ---
st.markdown("""
<style>
.sidebar button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: white !important;
    text-align: left !important;
    font-weight: normal !important;
    padding-left: 20px !important;
}
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
.sidebar button[aria-pressed="true"] {
    background: rgba(255,214,0,0.18) !important;
    border-left: 4px solid var(--accent) !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

# --- 8. Pomocnicze funkcje do obsługi widoków ---
# ... (tu wklej całą sekcję render_* z propozycji użytkownika) ...
# (ze względu na długość, kod render_* zostanie wklejony w całości w kolejnych krokach)

# --- 9. Wyświetlanie odpowiedniej sekcji na podstawie session_state ---
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