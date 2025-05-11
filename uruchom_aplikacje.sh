#!/bin/bash

# Kolory do formatowania wyjścia
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Nazwa katalogu wirtualnego środowiska
VENV_DIR="venv"

# Funkcja wyświetlająca kolorowe komunikaty
message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[UWAGA]${NC} $1"
}

error() {
    echo -e "${RED}[BŁĄD]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUKCES]${NC} $1"
}

# Sprawdzenie wersji Pythona
message "Sprawdzanie wersji Pythona..."
PYTHON_VERSION=$(python3 --version | cut -d " " -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 11 ]; then
    error "Python 3.11 lub nowszy jest wymagany. Znaleziono wersję $PYTHON_VERSION"
    exit 1
fi
success "Znaleziono Python $PYTHON_VERSION"

# Sprawdzenie i instalacja wymaganych pakietów systemowych
message "Sprawdzanie wymaganych pakietów systemowych..."

check_and_install() {
    if ! dpkg -l | grep -q $1; then
        warning "Pakiet $1 nie jest zainstalowany. Instalowanie..."
        sudo apt update
        sudo apt install -y $1
        if [ $? -ne 0 ]; then
            error "Nie udało się zainstalować pakietu $1"
            exit 1
        fi
        success "Pakiet $1 został zainstalowany"
    else
        message "Pakiet $1 jest już zainstalowany"
    fi
}

check_and_install tesseract-ocr
check_and_install poppler-utils
check_and_install python3-venv

# Tworzenie i aktywacja wirtualnego środowiska Python
message "Konfigurowanie wirtualnego środowiska Python..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        error "Nie udało się utworzyć wirtualnego środowiska Python"
        exit 1
    fi
    success "Utworzono wirtualne środowisko Python"
else
    message "Wirtualne środowisko Python już istnieje"
fi

# Aktywacja wirtualnego środowiska
source $VENV_DIR/bin/activate
if [ $? -ne 0 ]; then
    error "Nie udało się aktywować wirtualnego środowiska Python"
    exit 1
fi
success "Aktywowano wirtualne środowisko Python"

# Aktualizacja pip
message "Aktualizacja pip..."
pip install --upgrade pip
if [ $? -ne 0 ]; then
    warning "Nie udało się zaktualizować pip, ale kontynuuję..."
fi

# Sprawdzenie i instalacja wymaganych bibliotek Python
message "Instalacja wymaganych bibliotek Python w wirtualnym środowisku..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        error "Nie udało się zainstalować wymaganych bibliotek Python"
        exit 1
    fi
    # Dodatkowa instalacja pdf2image, jeśli nie ma w requirements.txt
    if ! grep -q "pdf2image" requirements.txt; then
        message "Instalacja pdf2image..."
        pip install pdf2image
    fi
    success "Wymagane biblioteki Python zostały zainstalowane w wirtualnym środowisku"
else
    error "Plik requirements.txt nie został znaleziony"
    exit 1
fi

# Sprawdzenie konfiguracji API Gemini
message "Sprawdzanie konfiguracji API Gemini..."
if [ ! -f ".env" ]; then
    warning "Plik .env nie istnieje. Tworzenie na podstawie .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        success "Utworzono plik .env na podstawie .env.example"
        warning "Musisz ustawić swój klucz API Gemini w pliku .env"
        warning "Otwórz plik .env i zastąp 'tu_wstaw_swoj_klucz_api' swoim rzeczywistym kluczem API"
        read -p "Naciśnij Enter, aby otworzyć plik .env w edytorze (lub Ctrl+C, aby anulować)... " -n 1 -r
        echo
        xdg-open .env || nano .env || gedit .env || vi .env
    else
        error "Plik .env.example nie istnieje. Tworzenie pustego pliku .env..."
        echo "GEMINI_API_KEY=tu_wstaw_swoj_klucz_api" > .env
        echo "GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent" >> .env
        warning "Utworzono pusty plik .env. Musisz ustawić swój klucz API Gemini."
        read -p "Naciśnij Enter, aby otworzyć plik .env w edytorze (lub Ctrl+C, aby anulować)... " -n 1 -r
        echo
        xdg-open .env || nano .env || gedit .env || vi .env
    fi
else
    message "Plik .env już istnieje"
    if ! grep -q "GEMINI_API_KEY" .env || grep -q "GEMINI_API_KEY=tu_wstaw_swoj_klucz_api" .env; then
        warning "Klucz API Gemini nie jest poprawnie skonfigurowany w pliku .env"
        read -p "Czy chcesz otworzyć plik .env do edycji? (t/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Tt]$ ]]; then
            xdg-open .env || nano .env || gedit .env || vi .env
        fi
    else
        success "Klucz API Gemini skonfigurowany"
    fi
fi

# Inicjalizacja bazy danych
message "Inicjalizacja bazy danych..."
python -c "from db.db_utils import init_db; init_db()"
if [ $? -ne 0 ]; then
    error "Nie udało się zainicjować bazy danych"
    exit 1
fi
success "Baza danych została zainicjowana"

# Uruchomienie aplikacji
message "Uruchamianie aplikacji..."
streamlit run app.py

# Deaktywacja wirtualnego środowiska (to się wykona tylko po zamknięciu aplikacji)
deactivate