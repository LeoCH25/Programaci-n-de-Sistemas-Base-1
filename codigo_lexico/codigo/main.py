"""Punto de entrada del Traductor HomeScript (PSB1).

Uso (desde la carpeta codigo/):
    python main.py                      analiza pruebas/ejemplo_pdf.txt
    python main.py pruebas/<archivo>.txt
    python main.py --todos              corre el banco de pruebas completo
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from homescript.config import CARPETA_PRUEBAS, EJEMPLO
from homescript.analizador import Resultado, analizar
from homescript.utilidades.archivos import leer_fuente, contar_lineas
from homescript.presentacion.consola import (SEPARADOR, codigos_de_error, imprimir_tokens,
                                             imprimir_estadisticas)
from homescript.errores.error_reporter import ErrorReporter

def analizar_archivo(ruta: Path, buffer_size: int = 4096, casillas: bool = False) -> Optional[Resultado]:
    if not ruta.exists() and (CARPETA_PRUEBAS / ruta).exists():
        ruta = CARPETA_PRUEBAS / ruta
    try:
        fuente, codificacion = leer_fuente(ruta)
    except OSError as e:
        print(f"[ERROR] No se pudo abrir '{ruta}': {e.strerror or e}")
        return None

    print(SEPARADOR)
    n = contar_lineas(fuente)
    print(f" TRADUCTOR HOMESCRIPT · {ruta.name} ({n} línea{'' if n == 1 else 's'}, {codificacion})")
    print(SEPARADOR)
    print("--- INICIANDO ANÁLISIS LÉXICO ---")

    r = analizar(fuente, buffer_size)
    eh = r.error_handler

    imprimir_tokens(r.tokens)
    print()
    r.tabla.imprimir()
    if casillas:
        print("\n=== CASILLAS DE LA TABLA HASH ===")
        r.tabla.imprimir_casillas()

    ErrorReporter.print_errors(eh.errores, eh.warnings, source_code=fuente)

    imprimir_estadisticas(r)
    if eh.has_errores:
        print("\n[AVISO] El análisis encontró errores. La ejecución posterior se ha detenido.")
    else:
        print("\n[OK] Análisis léxico y tabla de símbolos completados sin errores.")
    return r

def correr_banco(buffer_size: int = 4096) -> List[Tuple[str, Resultado]]:
    resultados = []
    for ruta in sorted(CARPETA_PRUEBAS.glob("*.txt")):
        fuente, _ = leer_fuente(ruta)
        resultados.append((ruta.name, analizar(fuente, buffer_size)))

    encabezado = ["ARCHIVO", "LÍNEAS", "TOKENS", "SÍMBOLOS", "ERRORES", "CÓDIGOS"]
    filas = [[nombre, str(contar_lineas(r.fuente)), str(len(r.tokens)), str(len(r.tabla)),
              str(r.error_handler.get_error_count()), codigos_de_error(r.error_handler) or "—"]
             for nombre, r in resultados]
    anchos = [max(len(f[c]) for f in [encabezado] + filas) for c in range(len(encabezado))]

    def renglon(celdas):
        return "  ".join(c.rjust(a) if 1 <= i <= 4 else c.ljust(a)
                         for i, (c, a) in enumerate(zip(celdas, anchos))).rstrip()

    print(f"=== BANCO DE PRUEBAS · {len(resultados)} programas en pruebas/ ===")
    print(renglon(encabezado))
    print("  ".join("-" * a for a in anchos))
    for fila in filas:
        print(renglon(fila))
    total = sum(r.error_handler.get_error_count() for _, r in resultados)
    print(f"\nTotal: {sum(len(r.tokens) for _, r in resultados)} tokens, "
          f"{sum(len(r.tabla) for _, r in resultados)} símbolos, {total} error(es).")
    print("Detalle de un archivo:  python main.py pruebas/<archivo>.txt")
    return resultados

def main(argumentos: Optional[List[str]] = None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass

    parser = argparse.ArgumentParser(
        description="Traductor HomeScript (PSB1): análisis léxico y tabla de símbolos.")
    parser.add_argument("archivos", nargs="*", type=Path,
                        help="programas a analizar (por omisión pruebas/ejemplo_pdf.txt)")
    parser.add_argument("--todos", action="store_true",
                        help="correr el banco de pruebas completo (una fila por pruebas/*.txt)")
    parser.add_argument("--casillas", action="store_true",
                        help="mostrar también el recorrido de la tabla hash casilla por casilla")
    parser.add_argument("--buffer", type=int, default=4096, metavar="N",
                        help="tamaño de cada mitad del buffer (por omisión 4096)")
    args = parser.parse_args(argumentos)
    if args.buffer < 1:
        parser.error("--buffer debe ser 1 o mayor")

    if args.todos:
        correr_banco(args.buffer)
        return

    for i, ruta in enumerate(args.archivos or [EJEMPLO]):
        if i:
            print("\n")
        analizar_archivo(ruta, args.buffer, args.casillas)

if __name__ == "__main__":
    main()