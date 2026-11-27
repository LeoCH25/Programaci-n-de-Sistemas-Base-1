"""Lectura de archivos fuente (deteccion de codificacion) y conteo de lineas."""
from pathlib import Path
from typing import Tuple

BOM_UTF16 = (b"\xff\xfe", b"\xfe\xff")


def leer_fuente(ruta: Path) -> Tuple[str, str]:
    if ruta.read_bytes()[:2] in BOM_UTF16:
        return ruta.read_text(encoding="utf-16"), "UTF-16"
    try:
        return ruta.read_text(encoding="utf-8-sig"), "UTF-8"
    except UnicodeDecodeError:
        return ruta.read_text(encoding="latin-1"), "Latin-1"


def contar_lineas(fuente: str) -> int:
    if not fuente:
        return 0
    return fuente.count("\n") + (0 if fuente.endswith("\n") else 1)
