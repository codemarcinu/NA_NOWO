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

    # Pobierz dynamiczne metryki z bazy
    from db.db_utils import count_all_products, count_expired_products, sum_expenses_current_month, count_expiring_soon_products
    liczba_produktow = count_all_products()
    liczba_przeterminowanych = count_expired_products()
    suma_wydatkow = sum_expenses_current_month()
    liczba_konczacych_sie = count_expiring_soon_products(3)

    # Karty metryczne
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="card metric">
            <i class="material-icons">inventory_2</i>
            <div>
                <div>Produkty w zapasie</div>
                <h2>{liczba_produktow}</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card metric">
            <i class="material-icons">watch_later</i>
            <div>
                <div>Produkty przeterminowane</div>
                <h2>{liczba_przeterminowanych}</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="card metric">
            <i class="material-icons">payments</i>
            <div>
                <div>Wydatki w tym miesiącu</div>
                <h2>{suma_wydatkow:.2f} zł</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Alerty
    if liczba_konczacych_sie > 0:
        st.markdown(f"""
        <div class="alert warning">
            <i class="material-icons">warning</i>
            <div>{liczba_konczacych_sie} produkt(ów) niedługo się przeterminuje (do 3 dni)</div>
        </div>
        """, unsafe_allow_html=True)
    if liczba_przeterminowanych > 0:
        st.markdown(f"""
        <div class="alert danger">
            <i class="material-icons">error</i>
            <div>{liczba_przeterminowanych} produkt(ów) jest już przeterminowanych!</div>
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
def aggregate_products(products):
    """
    Agreguje produkty o tej samej znormalizowanej nazwie i jednostce (sumuje ilość, rabat, cenę łączną).
    Pozostałe pola bierze z pierwszego wystąpienia.
    Zabezpieczenie: jeśli pole jest None, traktuj jako pusty string.
    """
    aggregated = {}
    for prod in products:
        nazwa = str(prod.get("nazwa_znormalizowana") or "").strip().lower()
        jednostka = str(prod.get("jednostka") or "").strip().lower()
        key = (nazwa, jednostka)
        if key in aggregated:
            aggregated[key]["ilosc"] += float(prod.get("ilosc", 0))
            aggregated[key]["cena_laczna"] += float(prod.get("cena_laczna", 0))
            aggregated[key]["rabat"] += float(prod.get("rabat", 0))
        else:
            # Kopiujemy produkt, żeby nie nadpisać oryginału
            aggregated[key] = prod.copy()
            # Upewniamy się, że liczby są float
            aggregated[key]["ilosc"] = float(prod.get("ilosc", 0))
            aggregated[key]["cena_laczna"] = float(prod.get("cena_laczna", 0))
            aggregated[key]["rabat"] = float(prod.get("rabat", 0))
    return list(aggregated.values())

def render_pending_receipts():
    st.title("Paragony oczekujące na przetworzenie")
    st.markdown("""
    **Jak działa ten moduł?**
    - Sprawdź tekst OCR, popraw jeśli trzeba.
    - Kliknij "Analizuj produkty przez LLM".
    - Edytuj produkty: nazwa, ilość, data ważności, ceny, rabat.
    - Rabat nie jest produktem! Jeśli LLM wykryje rabat jako produkt, usuń go ręcznie.
    - Wartości ujemne są automatycznie zamieniane na zero.
    - Produkty o tej samej nazwie i jednostce są sumowane przed zapisem do bazy.
    """)
    receipts = get_pending_receipts()
    if not receipts:
        st.info("Brak paragonów oczekujących na przetworzenie.")
        return
    for receipt in receipts:
        receipt_id, nazwa_pliku, sciezka, sklep, tekst_ocr, data_dodania = receipt
        st.markdown(f"""
        <div class="card">
            <h3>{nazwa_pliku}</h3>
            <p>Sklep: {sklep}</p>
            <p>Data dodania: {data_dodania}</p>
        </div>
        """, unsafe_allow_html=True)
        # 1. Podgląd pliku i tekstu OCR
        cols = st.columns([2, 3])
        with cols[0]:
            if os.path.exists(sciezka):
                if sciezka.lower().endswith(('jpg', 'jpeg', 'png')):
                    image = Image.open(sciezka)
                    st.image(image, caption=f"Podgląd: {nazwa_pliku}", width=300)
                elif sciezka.lower().endswith('pdf') and convert_from_path:
                    try:
                        images = convert_from_path(sciezka, first_page=1, last_page=1)
                        if images:
                            st.image(images[0], caption=f"Podgląd pierwszej strony: {nazwa_pliku}", width=300)
                    except Exception as e:
                        st.error(f"Błąd podglądu PDF: {str(e)}")
        with cols[1]:
            st.markdown("**Tekst OCR (możesz poprawić przed analizą):**")
            edited_ocr = st.text_area("", value=tekst_ocr, height=200, key=f"ocr_{receipt_id}")
        # 2. Analiza LLM
        if st.button("Analizuj produkty przez LLM", key=f"analyze_{receipt_id}"):
            try:
                st.info("Wysyłanie do analizy... To może potrwać chwilę.")
                log_event(f"Prompt do LLM (sklep: {sklep}): {edited_ocr[:100]}...")
                products = extract_products_from_receipt(edited_ocr, sklep)
                st.session_state[f"products_{receipt_id}"] = products
                st.success(f"Analiza zakończona. Wykryto {len(products)} produktów.")
            except Exception as e:
                st.error(f"Błąd analizy LLM: {str(e)}")
                log_event(f"Błąd LLM: {str(e)}")
        # 3. Edycja produktów (proste pola, obsługa rabatów i cen)
        key = f"products_{receipt_id}"
        if key in st.session_state:
            st.markdown("---")
            st.markdown("### Edytuj wykryte produkty")
            products = st.session_state[key]
            for i, prod in enumerate(products):
                st.markdown(f"#### Produkt #{i+1}")
                cols = st.columns(6)
                with cols[0]:
                    prod["nazwa_znormalizowana"] = st.text_input(f"Nazwa", value=prod.get("nazwa_znormalizowana", ""), key=f"nazwa_{receipt_id}_{i}")
                with cols[1]:
                    prod["ilosc"] = st.number_input(f"Ilość", value=max(0.0, float(prod.get("ilosc", 1))), min_value=0.0, key=f"ilosc_{receipt_id}_{i}")
                with cols[2]:
                    prod["data_waznosci"] = st.text_input(f"Data ważności (opcjonalnie)", value=prod.get("data_waznosci", ""), key=f"dataw_{receipt_id}_{i}")
                # Ceny i rabaty
                with cols[3]:
                    cena_jedn_przed = float(prod.get("cena_jednostkowa_przed", prod.get("cena_jednostkowa", 0)))
                    if cena_jedn_przed < 0:
                        st.warning("Cena jednostkowa przed rabatem była ujemna – poprawiono na 0.")
                    prod["cena_jednostkowa_przed"] = st.number_input(f"Cena jedn. przed rabatem", value=max(0.0, cena_jedn_przed), min_value=0.0, key=f"cena_jedn_przed_{receipt_id}_{i}")
                with cols[4]:
                    rabat = float(prod.get("rabat", 0))
                    if rabat < 0:
                        st.warning("Rabat był ujemny – poprawiono na 0.")
                    prod["rabat"] = st.number_input(f"Rabat", value=max(0.0, rabat), min_value=0.0, key=f"rabat_{receipt_id}_{i}")
                with cols[5]:
                    # Cena po rabacie = cena przed - rabat
                    cena_po = max(0.0, prod["cena_jednostkowa_przed"] - prod["rabat"])
                    prod["cena_jednostkowa"] = cena_po
                    st.number_input(f"Cena jedn. po rabacie", value=cena_po, min_value=0.0, key=f"cena_jedn_po_{receipt_id}_{i}", disabled=True)
                # Cena łączna (po rabacie)
                prod["cena_laczna"] = max(0.0, float(prod.get("cena_laczna", prod["cena_jednostkowa"] * prod["ilosc"])))
                st.number_input(f"Cena łączna (po rabacie)", value=prod["cena_laczna"], min_value=0.0, key=f"cena_laczna_{receipt_id}_{i}", disabled=True)
            # 4. Dodaj produkt ręcznie
            st.markdown("---")
            st.markdown("#### Dodaj produkt ręcznie (jeśli czegoś brakuje)")
            with st.form(f"manual_add_{receipt_id}"):
                nazwa = st.text_input("Nazwa produktu")
                ilosc = st.number_input("Ilość", min_value=0.0, value=1.0)
                dataw = st.text_input("Data ważności (opcjonalnie)")
                cena_jedn_przed = st.number_input("Cena jedn. przed rabatem", min_value=0.0, value=0.0)
                rabat = st.number_input("Rabat", min_value=0.0, value=0.0)
                cena_jedn_po = max(0.0, cena_jedn_przed - rabat)
                st.number_input("Cena jedn. po rabacie", value=cena_jedn_po, min_value=0.0, disabled=True)
                cena_laczna = max(0.0, cena_jedn_po * ilosc)
                st.number_input("Cena łączna (po rabacie)", value=cena_laczna, min_value=0.0, disabled=True)
                submit_manual = st.form_submit_button("Dodaj produkt")
                if submit_manual and nazwa:
                    manual_prod = {
                        "nazwa": nazwa,
                        "nazwa_znormalizowana": nazwa,
                        "ilosc": ilosc,
                        "data_waznosci": dataw,
                        "cena_jednostkowa_przed": cena_jedn_przed,
                        "rabat": rabat,
                        "cena_jednostkowa": cena_jedn_po,
                        "cena_laczna": cena_laczna
                    }
                    st.session_state[key].append(manual_prod)
                    st.success(f"Dodano produkt: {nazwa}")
            # 5. Zapisz produkty do bazy
            if st.button("Zapisz wszystkie produkty do bazy", key=f"save_all_{receipt_id}"):
                dodane = 0
                # AGREGACJA przed zapisem
                products_to_save = aggregate_products(st.session_state[key])
                st.info(f"Zagregowano {len(st.session_state[key])} pozycji do {len(products_to_save)} unikalnych produktów.")
                for prod in products_to_save:
                    try:
                        add_product(prod)
                        dodane += 1
                    except Exception as e:
                        st.error(f"Błąd dodawania produktu: {str(e)}")
                delete_pending_receipt(receipt_id)
                st.success(f"Dodano {dodane} produktów z paragonu {nazwa_pliku}. Paragon został usunięty z oczekujących.")
                st.rerun()
        # Usuń paragon
        if st.button("Usuń paragon", key=f"delete_{receipt_id}"):
            try:
                delete_pending_receipt(receipt_id)
                try:
                    if os.path.exists(sciezka):
                        os.unlink(sciezka)
                except:
                    pass
                st.success("Paragon został usunięty.")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd usuwania paragonu: {str(e)}")

# --- 5. Inne funkcje dla pozostałych widoków ---
def render_products_list():
    st.title("Lista produktów")
    st.markdown("""
    **Jak korzystać z listy produktów?**
    - Możesz filtrować produkty po nazwie, sklepie, kategorii, statusie lub dacie ważności.
    - Kliknij **Edytuj** przy wybranym produkcie, aby zmienić jego dane.
    - Kliknij **Usuń**, aby usunąć produkt (zostaniesz poproszony o potwierdzenie).
    """)

    # Pobierz produkty z bazy
    produkty = get_products()
    if not produkty:
        st.info("Brak produktów w bazie. Dodaj produkty przez OCR lub ręcznie.")
        return

    # Przygotuj DataFrame
    columns = [
        "ID", "Nazwa", "Nazwa znormalizowana", "Ilość", "Jednostka", "Kategoria", "Data ważności", "Sklep", "Cena jednostkowa", "Cena łączna", "Rabat", "Data zakupu", "Status", "Kategoria podatkowa", "Zamrożony", "Pewność"
    ]
    df = pd.DataFrame(produkty, columns=columns)

    # --- Filtrowanie ---
    with st.expander("Filtry", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            nazwa_filter = st.text_input("Filtruj po nazwie:")
        with col2:
            sklep_filter = st.text_input("Filtruj po sklepie:")
        with col3:
            kategoria_filter = st.text_input("Filtruj po kategorii:")
        with col4:
            status_filter = st.text_input("Filtruj po statusie:")
        # Data ważności (od-do)
        col5, col6 = st.columns(2)
        with col5:
            data_od = st.date_input("Data ważności od:", value=None, key="data_od")
        with col6:
            data_do = st.date_input("Data ważności do:", value=None, key="data_do")

    # Zastosuj filtry
    if nazwa_filter:
        df = df[df["Nazwa"].str.contains(nazwa_filter, case=False, na=False)]
    if sklep_filter:
        df = df[df["Sklep"].str.contains(sklep_filter, case=False, na=False)]
    if kategoria_filter:
        df = df[df["Kategoria"].str.contains(kategoria_filter, case=False, na=False)]
    if status_filter:
        df = df[df["Status"].str.contains(status_filter, case=False, na=False)]
    if data_od:
        df = df[df["Data ważności"].apply(lambda x: x and x >= str(data_od))]
    if data_do:
        df = df[df["Data ważności"].apply(lambda x: x and x <= str(data_do))]

    # --- Wyświetlanie tabeli ---
    st.markdown("### Tabela produktów")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Edycja i usuwanie ---
    st.markdown("### Edycja i usuwanie produktów")
    for idx, row in df.iterrows():
        with st.expander(f"Produkt: {row['Nazwa']} (ID: {row['ID']})"):
            st.write("**Szczegóły produktu:**")
            st.json(row.to_dict(), expanded=False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Edytuj", key=f"edit_{row['ID']}"):
                    with st.form(f"edit_form_{row['ID']}"):
                        nazwa = st.text_input("Nazwa", value=row["Nazwa"])
                        nazwa_znorm = st.text_input("Nazwa znormalizowana", value=row["Nazwa znormalizowana"])
                        ilosc = st.number_input("Ilość", value=float(row["Ilość"]), min_value=0.0)
                        jednostka = st.text_input("Jednostka", value=row["Jednostka"])
                        kategoria = st.text_input("Kategoria", value=row["Kategoria"])
                        data_waznosci = st.text_input("Data ważności (YYYY-MM-DD)", value=row["Data ważności"] or "")
                        sklep = st.text_input("Sklep", value=row["Sklep"])
                        cena_jednostkowa = st.number_input("Cena jednostkowa", value=float(row["Cena jednostkowa"] or 0), min_value=0.0)
                        cena_laczna = st.number_input("Cena łączna", value=float(row["Cena łączna"] or 0), min_value=0.0)
                        rabat = st.number_input("Rabat", value=float(row["Rabat"] or 0), min_value=0.0)
                        data_zakupu = st.text_input("Data zakupu (YYYY-MM-DD)", value=row["Data zakupu"] or "")
                        status = st.text_input("Status", value=row["Status"] or "")
                        kategoria_podatkowa = st.text_input("Kategoria podatkowa", value=row["Kategoria podatkowa"] or "")
                        zamrozony = st.checkbox("Zamrożony", value=bool(row["Zamrożony"]))
                        pewnosc = st.number_input("Pewność", value=int(row["Pewność"] or 0), min_value=0, max_value=100)
                        submit = st.form_submit_button("Zapisz zmiany")
                        if submit:
                            prod = {
                                "nazwa": nazwa,
                                "nazwa_znormalizowana": nazwa_znorm,
                                "ilosc": ilosc,
                                "jednostka": jednostka,
                                "kategoria": kategoria,
                                "data_waznosci": data_waznosci,
                                "sklep": sklep,
                                "cena_jednostkowa": cena_jednostkowa,
                                "cena_laczna": cena_laczna,
                                "rabat": rabat,
                                "data_zakupu": data_zakupu,
                                "status": status,
                                "kategoria_podatkowa": kategoria_podatkowa,
                                "zamrozony": int(zamrozony),
                                "pewnosc": pewnosc
                            }
                            try:
                                update_product(row["ID"], prod)
                                st.success("Produkt został zaktualizowany.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Błąd podczas aktualizacji: {str(e)}")
            with col2:
                if st.button("Usuń", key=f"delete_{row['ID']}"):
                    if st.confirm(f"Czy na pewno chcesz usunąć produkt '{row['Nazwa']}'?"):
                        try:
                            delete_product(row["ID"])
                            st.success("Produkt został usunięty.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Błąd podczas usuwania: {str(e)}")

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
    
    # Ustawienia modelu LLM
    st.subheader("Konfiguracja modelu językowego (LLM)")
    import dotenv
    import os
    from dotenv import load_dotenv
    load_dotenv()
    llm_type = os.getenv('LLM_TYPE', 'local')
    local_url = os.getenv('LOCAL_LLM_URL', 'http://192.168.0.167:1234/v1')
    local_model = os.getenv('LOCAL_LLM_MODEL', 'bielik-4.5b-v3.0-instruct')
    api_key = os.getenv('GEMINI_API_KEY', '')
    api_url = os.getenv('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent')

    selected_llm = st.radio(
        "Wybierz model LLM",
        options=["Lokalny (Bielik)", "Gemini API"],
        index=0 if llm_type == 'local' else 1
    )

    if selected_llm == "Lokalny (Bielik)":
        local_url = st.text_input("URL lokalnego modelu", value=local_url)
        local_model = st.text_input("Nazwa lokalnego modelu", value=local_model)
        # Sprawdź czy model jest dostępny
        try:
            import requests
            response = requests.get(f"{local_url}/models")
            if response.status_code == 200:
                st.success("Model lokalny jest dostępny!")
            else:
                st.error("Nie można połączyć się z lokalnym modelem. Sprawdź czy LM Studio jest uruchomione.")
        except Exception as e:
            st.error(f"Błąd podczas sprawdzania modelu lokalnego: {str(e)}")
    else:
        api_key = st.text_input("Klucz API Gemini", value=api_key, type="password")
        api_url = st.text_input("URL API Gemini", value=api_url)

    if st.button("Zapisz ustawienia LLM"):
        env_path = '.env'
        env_content = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key] = value.strip()
        env_content['LLM_TYPE'] = 'local' if selected_llm == "Lokalny (Bielik)" else 'gemini'
        if selected_llm == "Lokalny (Bielik)":
            env_content['LOCAL_LLM_URL'] = local_url
            env_content['LOCAL_LLM_MODEL'] = local_model
        else:
            env_content['GEMINI_API_KEY'] = api_key
            env_content['GEMINI_API_URL'] = api_url
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        dotenv.load_dotenv()
        st.success("Ustawienia LLM zostały zapisane.")
    
    # Pozostałe ustawienia...
    st.info("Pozostałe ustawienia aplikacji...")

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

# --- 9. Funkcja zmiany strony (bez rerun) ---
def change_page(page_id):
    st.session_state.page = page_id

# --- 10. Generowanie menu bocznego ---
for item in menu_data:
    # Określenie czy pozycja jest aktywna
    is_active = st.session_state.page == item["id"]
    menu_item_class = "active" if is_active else ""
    
    # Tworzenie przycisku menu
    st.sidebar.button(
        f"{item['label']}",
        key=f"menu_{item['id']}",
        help=f"Przejdź do sekcji {item['label']}",
        on_click=change_page,
        args=(item["id"],)
    )

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

# --- rerun po zmianie strony (po obsłudze przycisków) ---
if "last_page" not in st.session_state:
    st.session_state.last_page = st.session_state.page
if st.session_state.page != st.session_state.last_page:
    st.session_state.last_page = st.session_state.page
    st.rerun()