import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

CODIGO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODIGO))

from homescript.lexico.scanner import Scanner
from homescript.lexico.token_types import TokenType as T
from homescript.errores.error_types import (ErrorCode, CompilerError, NivelError,
                                            FaseError, ERRORES_LEXICOS)
from homescript.errores.error_handler import ErrorHandler
from homescript.errores.error_reporter import ErrorReporter

TAMANOS_BUFFER = [1, 2, 3, 5, 8, 16, 4096]

def analizar(fuente, n=4096):
    eh = ErrorHandler()
    tokens = Scanner(fuente, eh, buffer_size=n).scan_tokens()
    return tokens, eh

def salida_de(funcion, *args, **kwargs) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        funcion(*args, **kwargs)
    return buf.getvalue()

def test_catalogo_lexico():
    assert [e.codigo for e in ERRORES_LEXICOS.values()] == ["E1", "E2", "E3", "E4", "E5"]
    for e in ERRORES_LEXICOS.values():
        assert e.nivel == NivelError.ERROR and e.fase == FaseError.LEXICO
    err = CompilerError(ERRORES_LEXICOS["UNKNOWN_CHAR"], "Carácter no reconocido: '@'", 3, 7)
    assert str(err) == "[Léxico] Error E1: Carácter no reconocido: '@' (Línea 3, Columna 7)"

def test_error_handler():
    eh = ErrorHandler()
    assert not eh.has_errores and not eh.has_warnings
    aviso = ErrorCode("W1", "Aviso de prueba", NivelError.WARNING, FaseError.LEXICO)
    eh.report(aviso, "solo un aviso", 1, 1)
    assert eh.get_warning_count() == 1 and eh.get_error_count() == 0
    assert eh.has_warnings and not eh.has_errores

    eh.report_unknown_char("@", 2, 5, 10)
    assert eh.get_error_count() == 1 and eh.has_errores
    e = eh.errores[0]
    assert (e.error_codigo.codigo, e.linea, e.columna, e.posicion, e.contexto) == ("E1", 2, 5, 10, "@")

    fatal = ErrorCode("F1", "Fatal de prueba", NivelError.FATAL, FaseError.SEMANTICO)
    try:
        eh.report(fatal, "se detiene todo", 3, 1)
        assert False, "un FATAL debe lanzar excepción"
    except Exception as ex:
        assert "Error F1" in str(ex)
    assert eh.get_error_count() == 2

    eh.clear()
    assert eh.errores == [] and eh.warnings == []
    assert not eh.has_errores and not eh.has_warnings

ESPERADO = [
    ("E1", 2, 22, "ó"),
    ("E2", 4, 11, "2limite"),
    ("E3", 5, 20, "18."),
    ("E5", 6, 40, "!"),
    ("E4", 10, 29, '"Frio'),
]

def test_scanner_usa_el_handler():
    eh = ErrorHandler()
    s = Scanner("a @ b", eh)
    s.scan_tokens()
    assert s.error_handler is eh
    assert eh.get_error_count() == 1
    s2 = Scanner("@")
    s2.scan_tokens()
    assert isinstance(s2.error_handler, ErrorHandler) and s2.error_handler.has_errores

def test_programa_con_errores():
    fuente = (CODIGO / "pruebas" / "errores_lexicos.txt").read_text(encoding="utf-8")
    for n in TAMANOS_BUFFER:
        toks, eh = analizar(fuente, n)
        assert [(e.error_codigo.codigo, e.linea, e.columna, e.contexto) for e in eh.errores] == ESPERADO, n
        for e in eh.errores:
            assert fuente[e.posicion:e.posicion + len(e.contexto)] == e.contexto
        assert len(toks) == 32 and toks[-1].type == T.EOF
        assert eh.warnings == []

def test_contexto_con_puntero():
    fuente = "PARAMETRO 2limite = 30\n"
    _, eh = analizar(fuente)
    texto = ErrorReporter.format_error_with_context(eh.errores[0], fuente)
    assert texto.splitlines()[1:] == ["    PARAMETRO 2limite = 30",
                                      "              ^~~~~~~"]

def test_contexto_con_tabulador_y_crlf():
    fuente = 'ESTADO Noche {\r\n\tCUANDO t < 10 -> "Frio\r\n}'
    _, eh = analizar(fuente)
    linea, puntero = ErrorReporter.format_error_with_context(eh.errores[0], fuente).splitlines()[1:]
    assert linea == '    \tCUANDO t < 10 -> "Frio'
    assert eh.errores[0].columna == 19
    assert puntero == "    \t" + " " * 17 + "^~~~~"

def test_contexto_mismas_lineas_que_el_scanner():
    fuente = "x \x0c y\nz @"
    _, eh = analizar(fuente)
    assert [(e.contexto, e.linea) for e in eh.errores] == [("\x0c", 1), ("@", 2)]
    texto = ErrorReporter.format_error_with_context(eh.errores[1], fuente)
    assert texto.splitlines()[1:] == ["    z @", "      ^"]

def test_contexto_fuera_de_rango():
    err = CompilerError(ERRORES_LEXICOS["UNKNOWN_CHAR"], "x", 99, 1)
    assert ErrorReporter.format_error_with_context(err, "a\nb") == str(err)

def test_print_y_reporte():
    fuente = "a ! b @"
    _, eh = analizar(fuente)
    con = salida_de(ErrorReporter.print_errors, eh.errores, eh.warnings, source_code=fuente)
    assert "=== ERRORES ===" in con and "    a ! b @" in con
    assert con.strip().endswith("Resumen: 2 error(es), 0 advertencia(s).")
    sin = salida_de(ErrorReporter.print_errors, eh.errores, eh.warnings)
    assert sin.count("[ERROR]") == 2

    aviso = CompilerError(ErrorCode("W1", "Aviso", NivelError.WARNING, FaseError.LEXICO), "ojo", 1, 1)
    assert "ADVERTENCIAS" in salida_de(ErrorReporter.print_errors, [], [aviso])
    assert "ADVERTENCIAS" not in salida_de(ErrorReporter.print_errors, [], [aviso], show_warnings=False)

    reporte = ErrorReporter.generate_error_report(eh.errores, [aviso])
    assert reporte.count("[ERROR]") == 2 and reporte.count("[WARNING]") == 1
    assert reporte.endswith("Total: 2 error(es), 1 advertencia(s).")

if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK — {len(pruebas)} pruebas pasaron")
