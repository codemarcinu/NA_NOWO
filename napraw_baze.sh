#!/bin/bash

# Funkcja do dodawania kolumny jeśli nie istnieje
add_column_if_missing() {
    local column="$1"
    local type="$2"
    if ! sqlite3 produkty.db "PRAGMA table_info(produkty);" | grep -q "$column"; then
        echo "Dodaję kolumnę $column..."
        sqlite3 produkty.db "ALTER TABLE produkty ADD COLUMN $column $type;"
    else
        echo "Kolumna $column już istnieje."
    fi
}

add_column_if_missing "cena_laczna" "REAL"
add_column_if_missing "status" "TEXT"
add_column_if_missing "kategoria_podatkowa" "TEXT"
add_column_if_missing "zamrozony" "INTEGER"
add_column_if_missing "pewnosc" "INTEGER"
add_column_if_missing "nazwa_znormalizowana" "TEXT"

# Uzupełnij cena_laczna dla istniejących rekordów
echo "Uzupełniam wartości cena_laczna na podstawie ilosc * cena_jednostkowa..."
sqlite3 produkty.db "UPDATE produkty SET cena_laczna = ilosc * cena_jednostkowa WHERE cena_laczna IS NULL;"

echo "Naprawa zakończona!"