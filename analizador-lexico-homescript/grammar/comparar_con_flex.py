"""Compara el lexer hecho a mano (src/lexer.py) con el generado por Flex (homescript.l).

Para cada programa de tests/valid y tests/invalid (y, si se pide, programas
aleatorios) corre los dos analizadores y verifica que den exactamente los mismos
tokens y los mismos errores (tipo/código, línea, columna y lexema).

Requisitos: haber compilado antes la versión de Flex:
    cd grammar
    flex -o lex.yy.c homescript.l
    gcc lex.yy.c -o homescript_flex

Uso (desde la carpeta del proyecto):
    python grammar/comparar_con_flex.py                    usa grammar/homescript_flex
    python grammar/comparar_con_flex.py --aleatorios 500   además 500 programas al azar
    python grammar/comparar_con_flex.py --flex RUTA        otro ejecutable de Flex
"""
import argparse
import random
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from lexer import Lexer                    # noqa: E402
from main import leer_fuente, programas_de_prueba   # noqa: E402


def crudo_python(fuente: str):
    """Mismo formato crudo que imprime 'homescript_flex -c'."""
    lexer = Lexer(fuente)
    tokens = lexer.scan_tokens()
    lineas = [f"T {t.type.name} {t.linea} {t.columna} {t.value}" for t in tokens if not t.is_eof()]
    lineas += [f"E {e.error_codigo.codigo} {e.linea} {e.columna} {e.contexto}"
               for e in lexer.error_handler.errores]
    return lineas


def crudo_flex(ejecutable: Path, ruta: Path):
    salida = subprocess.run([str(ejecutable), "-c", str(ruta)], capture_output=True, check=True)
    return salida.stdout.decode("utf-8").splitlines()


# Piezas para armar programas al azar (válidas e inválidas).
PIEZAS = ["DISPOSITIVO", "SENSOR", "SI", "SINO", "Y", "NO", "VERDADERO", "clima", "x_1", "_a",
          "18", "60.5", "007", "18.", "2clima", "60.5abc", '"Modo noche"', '"sin cerrar',
          "+", "-", "*", "/", "->", ">", ">=", "<", "<=", "=", "==", "!=", "!", "{", "}", "(", ")",
          "@", "$", "#", ";", ",", ".", "&&", "'", "@var", "#define", "año", "calefacción", "€",
          "ñame", "x@y", "// comentario", ".5", "1,5", "0x1F", "SINOX", "si"]
SEPARADORES = [" ", "", "\n", "\t", "  ", "\r\n"]


def programa_aleatorio(rnd: random.Random) -> str:
    partes = []
    for _ in range(rnd.randint(0, 30)):
        partes.append(rnd.choice(PIEZAS))
        partes.append(rnd.choice(SEPARADORES))
    return "".join(partes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara el lexer en Python con el generado por Flex.")
    parser.add_argument("--flex", type=Path, default=RAIZ / "grammar" / "homescript_flex",
                        help="ejecutable generado con flex + gcc")
    parser.add_argument("--aleatorios", type=int, default=0, metavar="N",
                        help="además, comparar N programas generados al azar")
    args = parser.parse_args()
    ejecutable = args.flex
    if not ejecutable.exists() and ejecutable.with_suffix(".exe").exists():
        ejecutable = ejecutable.with_suffix(".exe")
    if not ejecutable.exists():
        print(f"No existe {ejecutable}. Compílalo primero (ver instrucciones arriba).")
        return 1

    diferentes = 0
    print(f"{'PROGRAMA':<46} {'TOKENS':>6} {'ERRORES':>7}  RESULTADO")
    for ruta in programas_de_prueba():
        py = crudo_python(leer_fuente(ruta)[0])
        fx = crudo_flex(ejecutable, ruta)
        iguales = py == fx
        diferentes += not iguales
        n_tok = sum(1 for l in py if l.startswith("T "))
        print(f"{ruta.parent.name + '/' + ruta.name:<46} {n_tok:>6} {len(py) - n_tok:>7}  "
              f"{'iguales' if iguales else 'DIFERENTES'}")

    if args.aleatorios:
        rnd = random.Random(2026)
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "aleatorio.txt"
            malos = 0
            for _ in range(args.aleatorios):
                fuente = programa_aleatorio(rnd)
                archivo.write_bytes(fuente.encode("utf-8"))
                if crudo_python(fuente.replace("\r\n", "\n")) != crudo_flex(ejecutable, archivo):
                    malos += 1
                    if malos == 1:
                        print("Primer programa aleatorio con diferencias:", repr(fuente))
            diferentes += malos
            print(f"{'programas aleatorios':<46} {args.aleatorios:>6} {'':>7}  "
                  f"{'iguales' if malos == 0 else f'{malos} DIFERENTES'}")

    print("\nResultado:", "los dos analizadores coinciden." if diferentes == 0
          else f"{diferentes} diferencia(s).")
    return 1 if diferentes else 0


if __name__ == "__main__":
    sys.exit(main())
