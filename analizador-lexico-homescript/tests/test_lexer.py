"""Pruebas del lexer: tokens, palabras reservadas, literales, línea/columna, errores y buffer.

Uso (desde la carpeta del proyecto):  python tests/test_lexer.py
"""
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from lexer import Lexer
from tokens import TokenType as T

TAMANOS_BUFFER = [1, 2, 3, 5, 8, 16, 4096]


def escanear(fuente, n=4096):
    lexer = Lexer(fuente, buffer_size=n)
    return lexer.scan_tokens(), lexer.error_handler.errores


def tipos(tokens):
    return [t.type for t in tokens]


def tvl(tokens):
    return [(t.type, t.value) for t in tokens if t.type != T.EOF]


def errores(errs):
    return [(e.error_codigo.codigo, e.contexto) for e in errs]


def test_ejemplo_especificacion():
    fuente = (RAIZ / "tests" / "valid" / "programa1_ejemplo_especificacion.txt").read_text(encoding="utf-8")
    base, errs = escanear(fuente)
    assert len(base) == 66, len(base)                  # 65 tokens + EOF
    assert errs == []
    assert base[21].type == T.FLOTANTE and base[21].literal == 60.5
    assert base[62].type == T.FLECHA
    assert (base[-1].type, base[-1].linea, base[-1].columna) == (T.EOF, 22, 1)
    for n in TAMANOS_BUFFER:                           # mismo resultado con cualquier buffer
        toks, errs = escanear(fuente, n)
        assert [(t.type, t.value, t.linea, t.columna, t.posicion, t.literal) for t in toks] == \
               [(t.type, t.value, t.linea, t.columna, t.posicion, t.literal) for t in base], n
        assert errs == []


def test_operadores_y_delimitadores():
    toks, errs = escanear("+ - * / -> > >= < <= = == != ( ) { }")
    assert tipos(toks) == [T.SUMA, T.RESTA, T.MULTIPLICACION, T.DIVISION, T.FLECHA,
                           T.MAYOR, T.MAYOR_IGUAL, T.MENOR, T.MENOR_IGUAL, T.ASIGNACION,
                           T.IGUAL, T.DIFERENTE, T.PAREN_IZQ, T.PAREN_DER,
                           T.LLAVE_IZQ, T.LLAVE_DER, T.EOF]
    assert errs == []
    toks, _ = escanear("a>=b->c==d-e")                 # lexema más largo, sin espacios
    assert tipos(toks) == [T.ID, T.MAYOR_IGUAL, T.ID, T.FLECHA, T.ID, T.IGUAL, T.ID,
                           T.RESTA, T.ID, T.EOF]
    assert [t.categoria() for t in toks[:-1]] == ["IDENTIFICADOR", "OPERADOR"] * 4 + ["IDENTIFICADOR"]


def test_palabras_reservadas():
    toks, _ = escanear("SI si SINO Y y NO VERDADERO FALSO _x x_1 SINOX")
    assert tipos(toks) == [T.SI, T.ID, T.SINO, T.Y, T.ID, T.NO, T.VERDADERO, T.FALSO,
                           T.ID, T.ID, T.ID, T.EOF]
    assert toks[6].literal is True and toks[7].literal is False
    assert [t.categoria() for t in toks[:3]] == ["PALABRA_RESERVADA", "IDENTIFICADOR", "PALABRA_RESERVADA"]


def test_literales():
    toks, errs = escanear('18 60.5 007 "Modo noche" ""')
    assert [(t.type, t.literal) for t in toks[:-1]] == [
        (T.ENTERO, 18), (T.FLOTANTE, 60.5), (T.ENTERO, 7),
        (T.CADENA, "Modo noche"), (T.CADENA, "")]
    assert toks[3].value == '"Modo noche"' and str(toks[3]) == '(CADENA, "Modo noche")'
    assert [t.categoria() for t in toks[:2]] == ["NUMERO_ENTERO", "NUMERO_FLOTANTE"]
    assert errs == []
    toks, _ = escanear("-5")                           # los números no llevan signo
    assert tipos(toks) == [T.RESTA, T.ENTERO, T.EOF]


def test_comentarios():
    toks, errs = escanear("a // comentario -> 5 \"x @ ñ\nb/c\n// al final sin salto")
    assert tvl(toks) == [(T.ID, "a"), (T.ID, "b"), (T.DIVISION, "/"), (T.ID, "c")]
    assert toks[1].linea == 2 and toks[-1].linea == 3
    assert errs == []


def test_linea_columna():
    toks, _ = escanear("x\n  y\n\tz\r\nw")
    assert [(t.value, t.linea, t.columna) for t in toks[:-1]] == [
        ("x", 1, 1), ("y", 2, 3), ("z", 3, 2), ("w", 4, 1)]


def test_identificadores_de_la_especificacion():
    toks, errs = escanear("variable1 my_function")
    assert tvl(toks) == [(T.ID, "variable1"), (T.ID, "my_function")] and errs == []
    toks, errs = escanear("123abc @var")
    assert tvl(toks) == []
    assert [(e.error_codigo.codigo, e.contexto, e.columna) for e in errs] == [
        ("E2", "123abc", 1), ("E6", "@var", 8)]
    assert str(errs[0]) == "Línea 1, Columna 1: Identificador inválido '123abc': no puede empezar con un dígito."


def test_errores():
    casos = {
        "@":              ([], [("E1", "@")]),
        "x = $ 5":        ([(T.ID, "x"), (T.ASIGNACION, "="), (T.ENTERO, "5")], [("E1", "$")]),
        "a && b":         ([(T.ID, "a"), (T.ID, "b")], [("E1", "&"), ("E1", "&")]),
        ".5":             ([(T.ENTERO, "5")], [("E1", ".")]),
        "'hola'":         ([(T.ID, "hola")], [("E1", "'"), ("E1", "'")]),
        "a € b":          ([(T.ID, "a"), (T.ID, "b")], [("E1", "€")]),
        "2clima = 3":     ([(T.ASIGNACION, "="), (T.ENTERO, "3")], [("E2", "2clima")]),
        "60.5abc":        ([], [("E2", "60.5abc")]),
        "0x1F":           ([], [("E2", "0x1F")]),
        "18. x":          ([(T.ID, "x")], [("E3", "18.")]),
        "18.a":           ([(T.ID, "a")], [("E3", "18.")]),
        '"Modo noche\nx': ([(T.ID, "x")], [("E4", '"Modo noche')]),
        '"abc':           ([], [("E4", '"abc')]),
        "a ! b":          ([(T.ID, "a"), (T.ID, "b")], [("E5", "!")]),
        "a!=b":           ([(T.ID, "a"), (T.DIFERENTE, "!="), (T.ID, "b")], []),
        "año":            ([], [("E6", "año")]),
        "ñame x":         ([(T.ID, "x")], [("E6", "ñame")]),
        "calefacción":    ([], [("E6", "calefacción")]),
        "#define PIN":    ([(T.ID, "PIN")], [("E6", "#define")]),
        "$temp_1 = 2":    ([(T.ASIGNACION, "="), (T.ENTERO, "2")], [("E6", "$temp_1")]),
        "x@y":            ([(T.ID, "x")], [("E6", "@y")]),
    }
    for fuente, (esperado_tokens, esperado_errores) in casos.items():
        for n in TAMANOS_BUFFER:
            toks, errs = escanear(fuente, n)
            assert tvl(toks) == esperado_tokens, (fuente, n, tvl(toks))
            assert errores(errs) == esperado_errores, (fuente, n, errores(errs))
            assert toks[-1].type == T.EOF
    _, errs = escanear('x = 1\n  "sin cerrar\ny')
    assert (errs[0].error_codigo.codigo, errs[0].linea, errs[0].columna) == ("E4", 2, 3)


LEXEMAS = {
    T.ID: ["clima", "x", "_a1", "humedad_max", "identificador_muy_largo_de_prueba_123"],
    T.ENTERO: ["0", "18", "123456789"],
    T.FLOTANTE: ["60.5", "0.0", "3.14159265"],
    T.CADENA: ['"Modo noche"', '""', '"a b c -> // x @ ñ"'],
    T.SI: ["SI"], T.SINO: ["SINO"], T.Y: ["Y"], T.FALSO: ["FALSO"],
    T.SUMA: ["+"], T.RESTA: ["-"], T.MULTIPLICACION: ["*"], T.DIVISION: ["/"],
    T.MAYOR: [">"], T.MAYOR_IGUAL: [">="], T.MENOR: ["<"], T.MENOR_IGUAL: ["<="],
    T.ASIGNACION: ["="], T.IGUAL: ["=="], T.DIFERENTE: ["!="], T.FLECHA: ["->"],
    T.LLAVE_IZQ: ["{"], T.LLAVE_DER: ["}"], T.PAREN_IZQ: ["("], T.PAREN_DER: [")"],
}
SEPARADORES = [" ", "  ", "\n", "\t", " // comentario\n", "\r\n"]


def test_buffer_aleatorio():
    """300 programas al azar: el resultado no depende del tamaño del buffer."""
    rnd = random.Random(2026)
    for _ in range(300):
        esperado, partes = [], []
        for _ in range(rnd.randint(0, 40)):
            tipo = rnd.choice(list(LEXEMAS))
            lexema = rnd.choice(LEXEMAS[tipo])
            esperado.append((tipo, lexema))
            partes.append(lexema)
            partes.append(rnd.choice(SEPARADORES))
        fuente = "".join(partes)
        for n in TAMANOS_BUFFER:
            toks, errs = escanear(fuente, n)
            assert tvl(toks) == esperado, (n, fuente)
            assert errs == [], (n, fuente, errores(errs))
            for t in toks[:-1]:
                assert fuente[t.posicion:t.posicion + len(t.value)] == t.value


def test_cargas_del_buffer():
    lexer = Lexer("a " * 50, buffer_size=8)
    lexer.scan_tokens()
    assert lexer.buffer.cargas == 13                   # 100 caracteres / 8 = 12.5 -> 13 mitades


if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK - {len(pruebas)} pruebas pasaron")
