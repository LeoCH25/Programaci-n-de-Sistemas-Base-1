"""Configuracion general del traductor HomeScript (rutas del proyecto)."""
from pathlib import Path

CARPETA_CODIGO = Path(__file__).resolve().parent.parent

CARPETA_PRUEBAS = CARPETA_CODIGO / "pruebas"
EJEMPLO = CARPETA_PRUEBAS / "ejemplo_pdf.txt"