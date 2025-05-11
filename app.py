import streamlit as st
import tempfile
import os
from ocr.ocr_utils import ocr_file
from llm.llm_utils import extract_products_from_receipt
from db.db_utils import add_product, init_db, get_products, update_product, delete_product, add_pending_receipt, get_pending_receipts, delete_pending_receipt
import pandas as pd
from datetime import datetime, timedelta
import logging
from PIL import Image
import re
import dotenv
import pathlib
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

# Konfiguracja loggera
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
def log_event(msg):
    logging.info(msg)
    st.write(f"[LOG] {msg}")

# Ustawienia strony
title = "🛒 Zarządzanie zakupami i zapasami spożywczymi"
st.set_page_config(page_title=title, layout="wide")

# --- 1. Funkcja ładowania CSS + Material Icons + Roboto ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("custom_theme.css")

# --- 2. Przełącznik motywu (Material Design) ---
st.markdown("""
<div class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">
    <i class="material-icons">dark_mode</i>
</div>
<script>
function toggleTheme() {
    document.body.classList.toggle('dark');
    const icon = document.querySelector('#theme-toggle i');
    if (document.body.classList.contains('dark')) {
        icon.textContent = 'light_mode';
    } else {
        icon.textContent = 'dark_mode';
    }
}
document.addEventListener('DOMContentLoaded', function() {
    document.body.classList.add('dark');
});
</script>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# --- 3. Sidebar menu z Material Icons ---
# Ukrywamy domyślne menu Streamlit
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

menu_data = [
    {"icon": "dashboard", "label": "Dashboard", "id": "Dashboard"},
    {"icon": "receipt", "label": "Dodaj paragon (OCR)", "id": "Dodaj paragon (OCR)"},
    {"icon": "pending", "label": "Paragony oczekujące na przetworzenie", "id": "Paragony oczekujące na przetworzenie"},
    {"icon": "inventory_2", "label": "Lista produktów", "id": "Lista produktów"},
    {"icon": "restaurant", "label": "Planowanie posiłków", "id": "Planowanie posiłków"},
    {"icon": "bar_chart", "label": "Analityka wydatków", "id": "Analityka wydatków"},
    {"icon": "settings", "label": "Ustawienia", "id": "Ustawienia"},
    {"icon": "shopping_cart", "label": "Lista zakupów", "id": "Lista zakupów"}
]

# Sidebar Material menu
st.sidebar.markdown("<h3>Menu</h3>", unsafe_allow_html=True)
for item in menu_data:
    menu_item_class = "menu-item"
    if 'menu' in st.session_state and st.session_state['menu'] == item["id"]:
        menu_item_class += " active"
    st.sidebar.markdown(f"""
    <div class="{menu_item_class}" onclick="window.location.hash='{item['id']}'">
        <i class="material-icons">{item['icon']}</i>
        <span>{item['label']}</span>
    </div>
    """, unsafe_allow_html=True)

# --- 4c. Synchronizacja hash -> session_state['menu'] ---
import streamlit as st
import urllib.parse
# Odczytaj hash z URL za pomocą nowej funkcji
hash_id = st.query_params.get('hash', [None])[0] if hasattr(st, 'query_params') else None
if not hash_id:
    import streamlit.components.v1 as components
    components.html('''<script>window.parent.postMessage({type: 'setMenu', value: window.location.hash.replace('#','')}, '*');</script>''', height=0)
    hash_id = None
if 'menu' not in st.session_state or not st.session_state['menu']:
    st.session_state['menu'] = 'Dashboard'
if hash_id and hash_id != st.session_state['menu']:
    st.session_state['menu'] = hash_id
menu = st.session_state['menu']

# --- 4b. Obsługa wyboru sekcji przez hash w URL (JS) i synchronizacja z session_state ---
import streamlit.components.v1 as components
st.markdown("""
<script>
window.addEventListener('hashchange', function() {
    const hash = window.location.hash.replace('#','');
    if (hash) {
        window.parent.postMessage({type: 'setMenu', value: hash}, '*');
    }
});
</script>
""", unsafe_allow_html=True)
components.html('''
<script>
window.parent.addEventListener('message', function(event) {
    if(event.data && event.data.type === 'setMenuPy') {
        window.location.hash = event.data.value;
    }
});
</script>
''', height=0)

# --- 5. Obsługa sekcji ---
if menu == "Dashboard":
    # Tutaj umieść kod dla sekcji Dashboard
    pass
elif menu == "Dodaj paragon (OCR)":
    # Tutaj umieść kod dla sekcji Dodaj paragon (OCR)
    pass
elif menu == "Paragony oczekujące na przetworzenie":
    # Tutaj umieść kod dla sekcji Paragony oczekujące na przetworzenie
    pass
elif menu == "Lista produktów":
    # Tutaj umieść kod dla sekcji Lista produktów
    pass
elif menu == "Planowanie posiłków":
    # Tutaj umieść kod dla sekcji Planowanie posiłków
    pass
elif menu == "Analityka wydatków":
    # Tutaj umieść kod dla sekcji Analityka wydatków
    pass
elif menu == "Ustawienia":
    # Tutaj umieść kod dla sekcji Ustawienia
    pass
elif menu == "Lista zakupów":
    # Tutaj umieść kod dla sekcji Lista zakupów
    pass