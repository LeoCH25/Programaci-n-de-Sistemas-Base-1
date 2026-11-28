"""Pruebas del programa principal (main.py) con todos los programas de tests/valid y tests/invalid.

Uso (desde la carpeta del proyecto):  python tests/test_main.py
"""
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import main as programa
from main import analizar, formatear_resultado, leer_fuente, programas_de_prueba
from tokens import TokenType as T

TAMANOS_BUFFER = [1, 2, 3, 5, 8, 16, 4096]

# archivo -> (tokens sin EOF, códigos de error en orden)
BANCO = {
    "programa1_ejemplo_especificacion.txt":   (65, []),
    "programa2_todos_los_tokens.txt":         (113, []),
    "programa3_invernadero.txt":              (96, []),
    "programa4_declaraciones.txt":            (41, []),
    "programa5_solo_comentarios.txt":         (0, []),
    "errores1_lexicos.txt":                   (33, ["E6", "E2", "E3", "E1", "E5", "E4"]),
    "errores2_identificadores_invalidos.txt": (28, ["E2", "E6", "E6", "E6", "E6", "E1", "E1", "E2"]),
    "errores3_habitos_de_c.txt":              (46, ["E6"] + ["E1"] * 6 + ["E2", "E1", "E1", "E5",
                                                                           "E1", "E1", "E1"]),
    "errores4_fin_de_archivo.txt":            (28, ["E3", "E4"]),
}


def salida_de(*argumentos) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        programa.main(list(argumentos))
    return buf.getvalue()


def codigos(r):
    return [e.error_codigo.codigo for e in r.errores_lexicos]


def test_banco_completo():
    nombres = [p.name for p in programas_de_prueba()]
    assert sorted(nombres) == sorted(BANCO), f"agrega el archivo nuevo a BANCO: {nombres}"
    for ruta in programas_de_prueba():
        r = analizar(leer_fuente(ruta)[0])
        assert (len(r.tokens_sin_eof), codigos(r)) == BANCO[ruta.name], (ruta.name, codigos(r))
        assert r.tokens[-1].type == T.EOF
        # Los programas válidos no tienen errores; los inválidos tienen al menos uno.
        assert (ruta.parent.name == "valid") == (codigos(r) == []), ruta


def test_banco_con_cualquier_buffer():
    for ruta in programas_de_prueba():
        fuente = leer_fuente(ruta)[0]
        base = analizar(fuente)
        for n in TAMANOS_BUFFER:
            r = analizar(fuente, n)
            assert [(t.type, t.value, t.linea, t.columna) for t in r.tokens] == \
                   [(t.type, t.value, t.linea, t.columna) for t in base.tokens], (ruta.name, n)
            assert [str(e) for e in r.errores_lexicos] == [str(e) for e in base.errores_lexicos]


def test_programa2_usa_los_36_tipos():
    r = analizar(leer_fuente(RAIZ / "tests" / "valid" / "programa2_todos_los_tokens.txt")[0])
    assert {t.type for t in r.tokens} == set(T) and len(T) == 36


def test_salidas_guardadas_estan_al_dia():
    """Cada archivo de tests/salidas es exactamente lo que produce hoy el lexer."""
    for ruta in programas_de_prueba():
        fuente, codificacion = leer_fuente(ruta)
        esperado = formatear_resultado(ruta, codificacion, analizar(fuente)) + "\n"
        guardado = (RAIZ / "tests" / "salidas" / f"{ruta.stem}_salida.txt").read_text(encoding="utf-8")
        assert guardado == esperado, f"regenera las salidas: python src/main.py --todos --guardar ({ruta.name})"


def test_formato_de_salida():
    con = salida_de()                                   # sin argumentos: ejemplo de la especificación
    lineas = con.splitlines()
    assert "programa1_ejemplo_especificacion.txt (21 líneas, UTF-8)" in lineas[1]
    assert lineas[3:7] == ["Lista de tokens:", '1: (PALABRA_RESERVADA, "DISPOSITIVO")',
                           '2: (IDENTIFICADOR, "clima")', '3: (PALABRA_RESERVADA, "DISPOSITIVO")']
    assert '22: (NUMERO_FLOTANTE, "60.5")' in lineas and '63: (OPERADOR, "->")' in lineas
    assert "No se encontraron errores léxicos." in lineas
    assert lineas[-1] == "Resumen: 65 tokens reconocidos, 0 errores léxicos."

    con = salida_de("errores2_identificadores_invalidos.txt")   # se busca en tests/invalid
    assert "Lista de errores:\nLínea 4, Columna 13: Identificador inválido '123abc': " \
           "no puede empezar con un dígito." in con
    assert con.rstrip().endswith("Resumen: 28 tokens reconocidos, 8 errores léxicos.")


def test_opciones_detalle_y_tabla():
    con = salida_de("errores4_fin_de_archivo.txt", "--detalle")
    assert "=== DETALLE DE TOKENS ===" in con and "=== ESTADÍSTICAS ===" in con
    assert "    PARAMETRO lleno = 95.\n                      ^~~" in con
    con = salida_de("programa4_declaraciones.txt", "--tabla")
    assert "=== TABLA DE SÍMBOLOS (10 símbolo(s), 101 casillas) ===" in con
    assert "[Semántico] E005 · Línea 8, Columna 13: 'clima' ya fue declarado" in con
    assert "No se encontraron errores léxicos." in con     # la tabla no mezcla sus errores


def test_leer_fuente():
    with tempfile.TemporaryDirectory() as carpeta:
        bom = Path(carpeta) / "bom.txt"                 # Bloc de notas: UTF-8 con BOM y \r\n
        bom.write_bytes(b"\xef\xbb\xbfSENSOR luz\r\n")
        texto, cod = leer_fuente(bom)
        assert cod == "UTF-8" and texto == "SENSOR luz\n"

        ansi = Path(carpeta) / "ansi.txt"
        ansi.write_bytes(b"DISPOSITIVO calefacci\xf3n\n")
        texto, cod = leer_fuente(ansi)
        assert cod == "ANSI" and texto == "DISPOSITIVO calefacción\n"

        for codificacion in ("utf-16-le", "utf-16-be"):   # PowerShell '>' o "Unicode" del Bloc de notas
            u16 = Path(carpeta) / f"{codificacion}.txt"
            u16.write_bytes("﻿SENSOR luz\r\nDISPOSITIVO foco\r\n".encode(codificacion))
            texto, cod = leer_fuente(u16)
            assert cod == "UTF-16" and texto == "SENSOR luz\nDISPOSITIVO foco\n", codificacion
            assert len(analizar(texto).tokens_sin_eof) == 4


def test_varios_archivos_y_no_encontrado():
    con = salida_de("programa5_solo_comentarios.txt", "no_existe.txt", "programa1_ejemplo_especificacion.txt")
    assert con.count("ANALIZADOR LÉXICO HOMESCRIPT") == 2
    assert "[ERROR] No se pudo abrir 'no_existe.txt'" in con
    assert "(el programa no tiene tokens: solo comentarios o espacios)" in con


def test_todos():
    con = salida_de("--todos", "--buffer", "3")
    assert "=== BANCO DE PRUEBAS · 9 programas (tests/valid y tests/invalid) ===" in con
    assert "valid    programa1_ejemplo_especificacion.txt        21      65        0  —" in con
    assert "invalid  errores1_lexicos.txt                        13      33        6  E1 E2 E3 E4 E5 E6" in con
    assert "Total: 450 tokens, 30 errores léxicos." in con


if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK - {len(pruebas)} pruebas pasaron")
