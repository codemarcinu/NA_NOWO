import pytesseract
from PIL import Image
import os

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

def ocr_image(file_path):
    """
    Przetwarza obraz (JPG/PNG) na tekst za pomocą Tesseract OCR.
    """
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang='pol')
    return text

def ocr_pdf(file_path):
    """
    Przetwarza plik PDF na tekst (strona po stronie) za pomocą Tesseract OCR.
    Wymaga biblioteki pdf2image.
    """
    if convert_from_path is None:
        raise ImportError("Zainstaluj pdf2image: pip install pdf2image")
    pages = convert_from_path(file_path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page, lang='pol') + "\n"
    return text

def ocr_file(file_path):
    """
    Wybiera odpowiednią metodę OCR w zależności od typu pliku.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png']:
        return ocr_image(file_path)
    elif ext == '.pdf':
        return ocr_pdf(file_path)
    else:
        raise ValueError("Obsługiwane są tylko pliki PDF, JPG, PNG.") 