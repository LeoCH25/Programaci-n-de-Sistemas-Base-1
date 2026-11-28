"""Pruebas del manejo y reporte de errores (errors.py).

Uso (desde la carpeta del proyecto):  python tests/test_errores.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from errors import (ERRORES_LEXICOS, CompilerError, ErrorCode, ErrorHandler, ErrorReporter,
                    FaseError, NivelError)
from lexer import Lexer
from tokens import TokenType as T

TAMANOS_BUFFER = [1, 2, 3, 5, 8, 16, 4096]


def analizar(fuente, n=4096):
    eh = ErrorHandler()
    tokens = Lexer(fuente, eh, buffer_size=n).scan_tokens()
    return tokens, eh


def test_catalogo_lexico():
    assert [e.codigo for e in ERRORES_LEXICOS.values()] == ["E1", "E2", "E3", "E4", "E5", "E6"]
    for e in ERRORES_LEXICOS.values():
        assert e.nivel == NivelError.ERROR and e.fase == FaseError.LEXICO


def test_formato_de_la_especificacion():
    _, eh = analizar("x = $ 5")
    assert str(eh.errores[0]) == "Línea 1, Columna 5: Símbolo desconocido '$' detectado."
    assert eh.errores[0].detalle() == "[Léxico] E1 · Línea 1, Columna 5: Símbolo desconocido '$' detectado."
    assert ErrorReporter.lista_errores(eh.errores) == [str(eh.errores[0])]


def test_pistas():
    _, eh = analizar("a;\nb && c\nPARAMETRO x = 'y'")
    mensajes = [e.mensaje for e in eh.errores]
    assert mensajes[0] == "Símbolo desconocido ';' detectado (HomeScript no usa ';' para terminar instrucciones)."
    assert mensajes[1] == "Símbolo desconocido '&' detectado (el Y lógico se escribe Y)."
    assert mensajes[3].endswith("(las cadenas van entre comillas dobles).")
    _, eh = analizar("año 60.5abc")
    assert eh.errores[0].mensaje == "Identificador inválido 'año': contiene el carácter no permitido 'ñ'."
    assert eh.errores[1].mensaje == "Número mal formado '60.5abc': tiene letras pegadas."


def test_error_handler():
    eh = ErrorHandler()
    assert not eh.has_errores
    aviso = ErrorCode("W1", "Aviso de prueba", NivelError.WARNING, FaseError.LEXICO)
    eh.report(aviso, "solo un aviso", 1, 1)
    assert len(eh.warnings) == 1 and eh.get_error_count() == 0 and not eh.has_errores

    eh.report_unknown_symbol("@", 2, 5, 10)
    e = eh.errores[0]
    assert (e.error_codigo.codigo, e.linea, e.columna, e.posicion, e.contexto) == ("E1", 2, 5, 10, "@")
    assert eh.has_errores

    fatal = ErrorCode("F1", "Fatal de prueba", NivelError.FATAL, FaseError.SEMANTICO)
    try:
        eh.report(fatal, "se detiene todo.", 3, 1)
        assert False, "un FATAL debe lanzar excepción"
    except RuntimeError as ex:
        assert "Línea 3, Columna 1" in str(ex)


def test_lexer_usa_el_handler():
    eh = ErrorHandler()
    lexer = Lexer("a @ b", eh)
    lexer.scan_tokens()
    assert lexer.error_handler is eh and eh.get_error_count() == 1
    solo = Lexer("@")                                  # sin handler, el lexer crea uno
    solo.scan_tokens()
    assert solo.error_handler.has_errores


ESPERADO_ERRORES1 = [
    ("E6", 3, 13, "calefacción"),
    ("E2", 5, 11, "2limite"),
    ("E3", 6, 20, "18."),
    ("E1", 7, 19, "$"),
    ("E5", 8, 40, "!"),
    ("E4", 12, 29, '"Frio'),
]


def test_programa_con_un_error_de_cada_tipo():
    fuente = (RAIZ / "tests" / "invalid" / "errores1_lexicos.txt").read_text(encoding="utf-8")
    for n in TAMANOS_BUFFER:
        toks, eh = analizar(fuente, n)
        assert [(e.error_codigo.codigo, e.linea, e.columna, e.contexto) for e in eh.errores] == \
               ESPERADO_ERRORES1, n
        for e in eh.errores:                           # la posición apunta al lexema con error
            assert fuente[e.posicion:e.posicion + len(e.contexto)] == e.contexto
        assert len(toks) == 34 and toks[-1].type == T.EOF   # el análisis siguió hasta el final


def test_contexto_con_puntero():
    fuente = "PARAMETRO 2limite = 30\n"
    _, eh = analizar(fuente)
    texto = ErrorReporter.con_contexto(eh.errores[0], fuente)
    assert texto.splitlines()[1:] == ["    PARAMETRO 2limite = 30",
                                      "              ^~~~~~~"]


def test_contexto_con_tabulador_y_crlf():
    fuente = 'ESTADO Noche {\r\n\tCUANDO t < 10 -> "Frio\r\n}'
    _, eh = analizar(fuente)
    linea, puntero = ErrorReporter.con_contexto(eh.errores[0], fuente).splitlines()[1:]
    assert linea == '    \tCUANDO t < 10 -> "Frio'
    assert eh.errores[0].columna == 19
    assert puntero == "    \t" + " " * 17 + "^~~~~"


def test_contexto_fuera_de_rango():
    err = CompilerError(ERRORES_LEXICOS["UNKNOWN_SYMBOL"], "x.", 99, 1)
    assert ErrorReporter.con_contexto(err, "a\nb") == err.detalle()


if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK - {len(pruebas)} pruebas pasaron")
