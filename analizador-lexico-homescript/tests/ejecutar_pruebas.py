"""Ejecuta todas las pruebas automáticas de tests/ (no necesita pytest).

Uso (desde la carpeta del proyecto):  python tests/ejecutar_pruebas.py
Cada archivo test_*.py también se puede correr por separado (o con pytest).
"""
import importlib.util
import sys
from pathlib import Path

CARPETA_TESTS = Path(__file__).resolve().parent


def main() -> int:
    total = 0
    for archivo in sorted(CARPETA_TESTS.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(archivo.stem, archivo)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        pruebas = [f for nombre, f in vars(modulo).items() if nombre.startswith("test_") and callable(f)]
        print(f"{archivo.name}:")
        for prueba in pruebas:
            prueba()
            print(f"  [OK] {prueba.__name__}")
        total += len(pruebas)
    print(f"\nOK - {total} pruebas pasaron")
    return 0


if __name__ == "__main__":
    sys.exit(main())
