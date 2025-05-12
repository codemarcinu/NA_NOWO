#!/bin/bash

# Dodaj kolumnę cena_laczna jeśli nie istnieje
if ! sqlite3 produkty.db "PRAGMA table_info(produkty);" | grep -q "cena_laczna"; then
    echo "Dodaję kolumnę cena_laczna..."
    sqlite3 produkty.db "ALTER TABLE produkty ADD COLUMN cena_laczna REAL;"
else
    echo "Kolumna cena_laczna już istnieje."
fi

# Uzupełnij cena_laczna dla istniejących rekordów
echo "Uzupełniam wartości cena_laczna na podstawie ilosc * cena_jednostkowa..."
sqlite3 produkty.db "UPDATE produkty SET cena_laczna = ilosc * cena_jednostkowa WHERE cena_laczna IS NULL;"

echo "Naprawa zakończona!"