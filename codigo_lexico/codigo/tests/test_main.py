import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

CODIGO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODIGO))

import main as programa
from main import analizar, leer_fuente, CARPETA_PRUEBAS
from homescript.tabla_simbolos.symbol_table import TipoDato
from homescript.lexico.token_types import TokenType as T

TAMANOS_BUFFER = [1, 2, 3, 5, 8, 16, 4096]
I = TipoDato.INDEFINIDO

BANCO = {
    "ejemplo_pdf.txt":     (66, 8, []),
    "errores_lexicos.txt": (32, 3, ["E1", "E2", "E3", "E5", "E4"]),
    "declaraciones.txt":   (42, 10, ["E005", "E005", "S001", "S002", "S002", "S002"]),
    "operadores.txt":      (114, 11, []),
    "errores_comunes.txt": (48, 7, ["E1"] * 7 + ["E2", "E1", "E1", "E5", "E1", "E1", "E1"]),
    "fin_de_archivo.txt":  (29, 4, ["E3", "E4"]),
    "vacio.txt":           (1, 0, []),
}

def resultado(nombre, n=4096):
    return analizar(leer_fuente(CARPETA_PRUEBAS / nombre)[0], n)

def codigos(r):
    return [e.error_codigo.codigo for e in r.error_handler.errores]

def salida_de(*argumentos) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        programa.main(list(argumentos))
    return buf.getvalue()

def test_banco_completo():
    en_carpeta = sorted(p.name for p in CARPETA_PRUEBAS.glob("*.txt"))
    assert en_carpeta == sorted(BANCO), f"agrega el archivo nuevo a BANCO: {en_carpeta}"
    for nombre, (n_tokens, n_simbolos, esperados) in BANCO.items():
        r = resultado(nombre)
        assert (len(r.tokens), len(r.tabla), codigos(r)) == (n_tokens, n_simbolos, esperados), \
            (nombre, len(r.tokens), len(r.tabla), codigos(r))
        assert r.tokens[-1].type == T.EOF and r.error_handler.warnings == []

def test_banco_con_cualquier_buffer():
    for nombre in BANCO:
        base = resultado(nombre)
        for n in TAMANOS_BUFFER:
            r = resultado(nombre, n)
            assert [(t.type, t.value, t.linea, t.columna) for t in r.tokens] == \
                   [(t.type, t.value, t.linea, t.columna) for t in base.tokens], (nombre, n)
            assert [(s.nombre, s.tipo, s.valor) for s in r.tabla] == \
                   [(s.nombre, s.tipo, s.valor) for s in base.tabla], (nombre, n)
            assert [(e.error_codigo.codigo, e.linea, e.columna) for e in r.error_handler.errores] == \
                   [(e.error_codigo.codigo, e.linea, e.columna) for e in base.error_handler.errores]

def test_operadores_usa_los_36_tipos():
    r = resultado("operadores.txt")
    assert {t.type for t in r.tokens} == set(T) and len(T) == 36
    assert [(s.nombre, s.tipo.value, s.valor) for s in r.tabla][6:] == [
        ("minimo", "entero", 18), ("margen", "flotante", 2.5), ("aviso", "cadena", "Modo ahorro"),
        ("automatico", "booleano", True), ("manual", "booleano", False)]

def test_errores_comunes():
    r = resultado("errores_comunes.txt")
    errores = [(e.error_codigo.codigo, e.linea, e.columna, e.contexto) for e in r.error_handler.errores]
    assert errores[:8] == [
        ("E1", 2, 1, "#"), ("E1", 3, 17, ";"), ("E1", 5, 23, ";"), ("E1", 6, 20, "."),
        ("E1", 7, 22, ","), ("E1", 8, 20, "'"), ("E1", 8, 25, "'"), ("E2", 9, 21, "0x1F")]
    assert [(e[0], e[3]) for e in errores[8:]] == [
        ("E1", "&"), ("E1", "&"), ("E5", "!"), ("E1", ";"), ("E1", "|"), ("E1", "|")]
    assert [(s.nombre, s.tipo, s.valor) for s in r.tabla] == [
        ("foco", TipoDato.ENTIDAD, None), ("luz", TipoDato.ENTIDAD, None),
        ("limite", TipoDato.ENTERO, 500),
        ("factor", I, None),
        ("decimal", I, None),
        ("nombre", I, None), ("mascara", I, None)]

def test_valor_partido_por_error_lexico():
    casos = {
        "PARAMETRO x = .5":      (I, None),
        "PARAMETRO x = @18":     (I, None),
        "PARAMETRO x = 1,5":     (I, None),
        "PARAMETRO x = 18.5.3":  (I, None),
        "PARAMETRO x = 1, 5":    (TipoDato.ENTERO, 1),
        "PARAMETRO x = 500;":    (TipoDato.ENTERO, 500),
        "PARAMETRO x = 7 @":     (TipoDato.ENTERO, 7),
        "PARAMETRO x = 2\n@3":   (TipoDato.ENTERO, 2),
    }
    for fuente, esperado in casos.items():
        r = analizar(fuente)
        assert (r.tabla.buscar("x").tipo, r.tabla.buscar("x").valor) == esperado, fuente
        assert all(c.startswith("E") and len(c) == 2 for c in codigos(r)), (fuente, codigos(r))

def test_fin_de_archivo():
    fuente = (CARPETA_PRUEBAS / "fin_de_archivo.txt").read_text(encoding="utf-8")
    assert not fuente.endswith("\n")
    r = resultado("fin_de_archivo.txt")
    e3, e4 = r.error_handler.errores
    assert (e3.linea, e3.columna, e3.contexto) == (4, 19, "95.")
    assert (e4.linea, e4.columna, e4.contexto) == (11, 21, '"Tanque lleno')
    assert (r.tokens[-1].linea, r.tokens[-1].columna) == (11, 34)
    assert [(s.nombre, s.tipo) for s in r.tabla][2:] == [("lleno", I), ("mensaje", I)]

def test_leer_fuente():
    with tempfile.TemporaryDirectory() as carpeta:
        bom = Path(carpeta) / "bom.txt"
        bom.write_bytes(b"\xef\xbb\xbfSENSOR luz\r\n")
        texto, cod = leer_fuente(bom)
        assert cod == "UTF-8" and texto == "SENSOR luz\n"
        assert codigos(analizar(texto)) == []

        ansi = Path(carpeta) / "ansi.txt"
        ansi.write_bytes(b"DISPOSITIVO calefacci\xf3n\n")
        texto, cod = leer_fuente(ansi)
        assert cod == "Latin-1" and texto == "DISPOSITIVO calefacción\n"

        for codificacion in ("utf-16-le", "utf-16-be"):
            u16 = Path(carpeta) / f"{codificacion}.txt"
            u16.write_bytes("﻿SENSOR luz\r\nDISPOSITIVO foco\r\n".encode(codificacion))
            texto, cod = leer_fuente(u16)
            assert cod == "UTF-16" and texto == "SENSOR luz\nDISPOSITIVO foco\n", codificacion
            r = analizar(texto)
            assert (len(r.tokens), len(r.tabla), codigos(r)) == (5, 2, [])

def test_salida_sin_errores():
    con = salida_de()
    secciones = ["TRADUCTOR HOMESCRIPT · ejemplo_pdf.txt (21 líneas, UTF-8)",
                 "--- INICIANDO ANÁLISIS LÉXICO ---", "=== TOKENS GENERADOS (66) ===",
                 "=== TABLA DE SÍMBOLOS (8 símbolo(s), 101 casillas) ===",
                 "Resumen: 0 error(es), 0 advertencia(s).", "=== ESTADÍSTICAS ===",
                 "[OK] Análisis léxico y tabla de símbolos completados sin errores."]
    posiciones = [con.index(s) for s in secciones]
    assert posiciones == sorted(posiciones)
    assert "Símbolos:      8 (5 entidad, 2 entero, 1 flotante)" in con
    assert "  63  FLECHA          '->'" in con
    assert "=== ERRORES ===" not in con and "CASILLAS" not in con

def test_salida_con_errores():
    con = salida_de("declaraciones.txt", "--casillas")
    assert "=== ERRORES ===" in con and "=== CASILLAS DE LA TABLA HASH ===" in con
    assert "Errores:       6 (Sintáctico 4, Semántico 2) · E005×2 S001 S002×3" in con
    assert con.rstrip().endswith("[AVISO] El análisis encontró errores. La ejecución posterior se ha detenido.")

def test_varios_archivos_y_no_encontrado():
    con = salida_de("vacio.txt", "no_existe.txt", "ejemplo_pdf.txt")
    assert con.count("TRADUCTOR HOMESCRIPT") == 2
    assert "[ERROR] No se pudo abrir 'no_existe.txt'" in con
    assert "vacio.txt (3 líneas, UTF-8)" in con and "(vacía)" in con

def test_todos():
    con = salida_de("--todos", "--buffer", "3")
    assert "=== BANCO DE PRUEBAS · 7 programas en pruebas/ ===" in con
    assert "errores_comunes.txt      15      48         7       14  E1×12 E2 E5" in con
    assert "ejemplo_pdf.txt          21      66         8        0  —" in con
    assert "declaraciones.txt        14      42        10        6  E005×2 S001 S002×3" in con
    assert "Total: 332 tokens, 43 símbolos, 27 error(es)." in con

if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK — {len(pruebas)} pruebas pasaron")
