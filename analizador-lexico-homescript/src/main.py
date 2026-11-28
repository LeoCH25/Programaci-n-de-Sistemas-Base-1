"""main.py - Punto de entrada del analizador léxico de HomeScript.

Lee un archivo de texto con un programa HomeScript, invoca al lexer y muestra:
  1. La lista ordenada de tokens:   1: (PALABRA_RESERVADA, "DISPOSITIVO")
  2. La lista de errores léxicos:   Línea 2, Columna 1: Identificador inválido '123abc': ...

Uso (desde la carpeta del proyecto):
    python src/main.py tests/valid/programa1_ejemplo_especificacion.txt
    python src/main.py archivo.txt --detalle   tipo, línea y columna de cada token y contexto
                                               de cada error
    python src/main.py archivo.txt --tabla     además, la tabla de símbolos (módulo extra)
    python src/main.py archivo.txt --guardar   guarda la salida en tests/salidas/
    python src/main.py --todos                 banco de pruebas: todos los programas de tests/
    python src/main.py --todos --guardar       regenera todas las salidas de tests/salidas/
"""
import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from errors import ErrorHandler, ErrorReporter, FaseError
from lexer import Lexer
from tabla_simbolos import SymbolTable
from tokens import Token

RAIZ = Path(__file__).resolve().parent.parent          # carpeta del proyecto
CARPETA_TESTS = RAIZ / "tests"
CARPETAS_PROGRAMAS = [CARPETA_TESTS / "valid", CARPETA_TESTS / "invalid"]
CARPETA_SALIDAS = CARPETA_TESTS / "salidas"
EJEMPLO = CARPETA_TESTS / "valid" / "programa1_ejemplo_especificacion.txt"
SEPARADOR = "=" * 78


@dataclass
class Resultado:
    """Todo lo que produce el análisis de un archivo."""
    fuente: str
    tokens: List[Token]          # incluye el token EOF al final
    error_handler: ErrorHandler
    tabla: Optional[SymbolTable] = None
    cargas_buffer: int = 0

    @property
    def tokens_sin_eof(self) -> List[Token]:
        return [t for t in self.tokens if not t.is_eof()]

    @property
    def errores_lexicos(self):
        return [e for e in self.error_handler.errores
                if e.error_codigo.fase == FaseError.LEXICO]

    @property
    def errores_tabla(self):
        return [e for e in self.error_handler.errores
                if e.error_codigo.fase != FaseError.LEXICO]


def analizar(fuente: str, buffer_size: int = 4096, con_tabla: bool = False) -> Resultado:
    """Invoca al lexer (y, si se pide, llena la tabla de símbolos). No imprime nada."""
    error_handler = ErrorHandler()
    lexer = Lexer(fuente, error_handler, buffer_size=buffer_size)
    tokens = lexer.scan_tokens()
    tabla = None
    if con_tabla:
        tabla = SymbolTable(error_handler)
        tabla.llenar(tokens)
    return Resultado(fuente, tokens, error_handler, tabla, lexer.buffer.cargas)


# ----- Lectura de archivos -----

BOM_UTF16 = (b"\xff\xfe", b"\xfe\xff")


def leer_fuente(ruta: Path) -> Tuple[str, str]:
    """Lee el archivo detectando su codificación (UTF-8 con o sin BOM, UTF-16 o ANSI).

    Los saltos de línea de Windows (\\r\\n) se convierten en \\n.
    """
    datos = ruta.read_bytes()
    if datos[:2] in BOM_UTF16:
        texto, codificacion = datos.decode("utf-16"), "UTF-16"
    else:
        try:
            texto, codificacion = datos.decode("utf-8-sig"), "UTF-8"
        except UnicodeDecodeError:
            texto, codificacion = datos.decode("latin-1"), "ANSI"
    return texto.replace("\r\n", "\n"), codificacion


def contar_lineas(fuente: str) -> int:
    if not fuente:
        return 0
    return fuente.count("\n") + (0 if fuente.endswith("\n") else 1)


def resolver_ruta(ruta: Path) -> Path:
    """Si el archivo no existe tal cual, se busca por nombre en tests/valid y tests/invalid."""
    if ruta.exists():
        return ruta
    for carpeta in CARPETAS_PROGRAMAS:
        if (carpeta / ruta.name).exists():
            return carpeta / ruta.name
    return ruta


def ruta_visible(ruta: Path) -> str:
    """Ruta relativa a la carpeta del proyecto (más corta y sin datos de la computadora)."""
    try:
        return ruta.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return ruta.name


# ----- Formato de salida -----

def formatear_lista_tokens(tokens: List[Token]) -> List[str]:
    """Formato de la especificación: 'n: (CATEGORIA, "lexema")'."""
    lineas = ["Lista de tokens:"]
    lineas += [f"{i}: {t}" for i, t in enumerate(tokens, 1)]
    if not tokens:
        lineas.append("(el programa no tiene tokens: solo comentarios o espacios)")
    return lineas


def formatear_lista_errores(r: Resultado) -> List[str]:
    if not r.errores_lexicos:
        return ["No se encontraron errores léxicos."]
    return ["Lista de errores:"] + ErrorReporter.lista_errores(r.errores_lexicos)


def formatear_detalle(r: Resultado) -> List[str]:
    """Tipo, línea y columna de cada token; errores con su contexto; estadísticas."""
    lineas = ["", "=== DETALLE DE TOKENS ==="]
    lineas.append(f"{'#':>4}  {'TIPO':<14} {'LEXEMA':<16} {'LÍN':>4} {'COL':>4}  "
                  f"{'CATEGORÍA':<17} {'DESCRIPCIÓN':<27} LITERAL")
    for i, t in enumerate(r.tokens, 1):
        literal = "" if t.literal is None else repr(t.literal)
        lineas.append(f"{i:>4}  {t.type.name:<14} {t.value!r:<16} {t.linea:>4} "
                      f"{t.columna:>4}  {t.categoria():<17} {t.descripcion():<27} "
                      f"{literal}".rstrip())
    if r.errores_lexicos:
        lineas += ["", "=== ERRORES LÉXICOS (con su línea de código) ==="]
        lineas += [ErrorReporter.con_contexto(e, r.fuente) for e in r.errores_lexicos]
    lineas += ["", "=== ESTADÍSTICAS ==="]
    lineas.append(f"Tokens: {len(r.tokens_sin_eof)} (+ EOF) · "
                  f"cargas del buffer: {r.cargas_buffer}")
    for categoria, n in Counter(t.categoria() for t in r.tokens_sin_eof).most_common():
        lineas.append(f"  {categoria:<20}{n:>4}")
    if r.errores_lexicos:
        cuenta = Counter(e.error_codigo.codigo for e in r.errores_lexicos)
        lineas.append("Errores léxicos: "
                      + ", ".join(f"{c}×{n}" for c, n in sorted(cuenta.items())))
    return lineas


def formatear_tabla(r: Resultado) -> List[str]:
    lineas = ["", r.tabla.formatear()]
    if r.errores_tabla:
        lineas += ["", "Errores de la tabla de símbolos:"]
        lineas += [e.detalle() for e in r.errores_tabla]
    return lineas


def formatear_resultado(ruta: Path, codificacion: str, r: Resultado,
                        detalle: bool = False, tabla: bool = False) -> str:
    n = contar_lineas(r.fuente)
    lineas = [SEPARADOR,
              f" ANALIZADOR LÉXICO HOMESCRIPT · {ruta_visible(ruta)} "
              f"({n} línea{'' if n == 1 else 's'}, {codificacion})",
              SEPARADOR]
    lineas += formatear_lista_tokens(r.tokens_sin_eof)
    lineas.append("")
    lineas += formatear_lista_errores(r)
    if detalle:
        lineas += formatear_detalle(r)
    if tabla:
        lineas += formatear_tabla(r)
    total = len(r.errores_lexicos)
    errores = "1 error léxico" if total == 1 else f"{total} errores léxicos"
    lineas += ["", f"Resumen: {len(r.tokens_sin_eof)} tokens reconocidos, {errores}."]
    return "\n".join(lineas)


# ----- Comandos -----

def guardar_salida(ruta: Path, texto: str) -> Path:
    CARPETA_SALIDAS.mkdir(parents=True, exist_ok=True)
    destino = CARPETA_SALIDAS / f"{ruta.stem}_salida.txt"
    destino.write_text(texto + "\n", encoding="utf-8")
    return destino


def analizar_archivo(ruta: Path, buffer_size: int = 4096, detalle: bool = False,
                     tabla: bool = False, guardar: bool = False) -> Optional[Resultado]:
    ruta = resolver_ruta(ruta)
    try:
        fuente, codificacion = leer_fuente(ruta)
    except OSError as e:
        print(f"[ERROR] No se pudo abrir '{ruta}': {e.strerror or e}")
        return None
    r = analizar(fuente, buffer_size, con_tabla=tabla)
    texto = formatear_resultado(ruta, codificacion, r, detalle, tabla)
    print(texto)
    if guardar:
        print(f"[Salida guardada en {ruta_visible(guardar_salida(ruta, texto))}]")
    return r


def programas_de_prueba() -> List[Path]:
    return [ruta for carpeta in CARPETAS_PROGRAMAS for ruta in sorted(carpeta.glob("*.txt"))]


def correr_banco(buffer_size: int = 4096,
                 guardar: bool = False) -> List[Tuple[Path, Resultado]]:
    """Analiza cada programa de tests/valid y tests/invalid; muestra una fila por archivo."""
    resultados = []
    for ruta in programas_de_prueba():
        fuente, codificacion = leer_fuente(ruta)
        r = analizar(fuente, buffer_size)
        resultados.append((ruta, r))
        if guardar:
            guardar_salida(ruta, formatear_resultado(ruta, codificacion, r))

    encabezado = ["CARPETA", "ARCHIVO", "LÍNEAS", "TOKENS", "ERRORES", "CÓDIGOS"]
    filas = []
    for ruta, r in resultados:
        cuenta = Counter(e.error_codigo.codigo for e in r.errores_lexicos)
        codigos = " ".join(c if n == 1 else f"{c}×{n}" for c, n in sorted(cuenta.items()))
        filas.append([ruta.parent.name, ruta.name, str(contar_lineas(r.fuente)),
                      str(len(r.tokens_sin_eof)), str(len(r.errores_lexicos)),
                      codigos or "—"])
    anchos = [max(len(f[c]) for f in [encabezado] + filas) for c in range(len(encabezado))]

    def renglon(celdas):
        return "  ".join(c.rjust(a) if 2 <= i <= 4 else c.ljust(a)
                         for i, (c, a) in enumerate(zip(celdas, anchos))).rstrip()

    print(f"=== BANCO DE PRUEBAS · {len(resultados)} programas "
          "(tests/valid y tests/invalid) ===")
    print(renglon(encabezado))
    print("  ".join("-" * a for a in anchos))
    for fila in filas:
        print(renglon(fila))
    total_tokens = sum(len(r.tokens_sin_eof) for _, r in resultados)
    total_errores = sum(len(r.errores_lexicos) for _, r in resultados)
    print(f"\nTotal: {total_tokens} tokens, {total_errores} errores léxicos.")
    if guardar:
        print(f"[Salidas guardadas en tests/salidas/ ({len(resultados)} archivos)]")
    return resultados


def main(argumentos: Optional[List[str]] = None):
    # Evita que la consola de Windows truene con caracteres que no puede mostrar.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass

    parser = argparse.ArgumentParser(
        description="Analizador léxico de HomeScript: convierte un programa en una lista "
                    "de tokens y reporta los errores léxicos con su línea y columna.")
    parser.add_argument("archivos", nargs="*", type=Path,
                        help="programas a analizar (por omisión, el ejemplo de la "
                             "especificación)")
    parser.add_argument("--detalle", action="store_true",
                        help="mostrar tipo, línea y columna de cada token y el "
                             "contexto de cada error")
    parser.add_argument("--tabla", action="store_true",
                        help="mostrar también la tabla de símbolos (módulo extra)")
    parser.add_argument("--guardar", action="store_true",
                        help="guardar la salida en tests/salidas/<archivo>_salida.txt")
    parser.add_argument("--todos", action="store_true",
                        help="analizar todos los programas de tests/valid y tests/invalid")
    parser.add_argument("--buffer", type=int, default=4096, metavar="N",
                        help="tamaño de cada mitad del buffer doble (por omisión 4096)")
    args = parser.parse_args(argumentos)
    if args.buffer < 1:
        parser.error("--buffer debe ser 1 o mayor")

    if args.todos:
        correr_banco(args.buffer, args.guardar)
        return

    for i, ruta in enumerate(args.archivos or [EJEMPLO]):
        if i:
            print()
        analizar_archivo(ruta, args.buffer, args.detalle, args.tabla, args.guardar)


if __name__ == "__main__":
    main()
