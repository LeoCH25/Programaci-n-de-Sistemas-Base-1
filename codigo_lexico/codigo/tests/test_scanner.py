import random
import sys
from pathlib import Path

CODIGO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODIGO))

from homescript.lexico.scanner import Scanner
from homescript.lexico.token_types import TokenType as T

TAMANOS_BUFFER = [1, 2, 3, 5, 8, 16, 4096]

def escanear(fuente, n=4096):
    s = Scanner(fuente, buffer_size=n)
    return s.scan_tokens(), s.error_handler.errores

def tipos(tokens):
    return [t.type for t in tokens]

def tvl(tokens):
    return [(t.type, t.value) for t in tokens if t.type != T.EOF]

def errores(errs):
    return [(e.error_codigo.codigo, e.contexto) for e in errs]

def test_ejemplo_pdf():
    fuente = (CODIGO / "pruebas" / "ejemplo_pdf.txt").read_text(encoding="utf-8")
    base, errs = escanear(fuente)
    assert len(base) == 66, len(base)
    assert errs == []
    assert base[21].type == T.FLOTANTE and base[21].literal == 60.5
    assert base[62].type == T.FLECHA
    assert (base[-1].type, base[-1].linea, base[-1].columna) == (T.EOF, 22, 1)
    for n in TAMANOS_BUFFER:
        toks, errs = escanear(fuente, n)
        assert [(t.type, t.value, t.linea, t.columna, t.posicion, t.literal) for t in toks] == \
               [(t.type, t.value, t.linea, t.columna, t.posicion, t.literal) for t in base], n
        assert errs == []

def test_operadores():
    toks, errs = escanear("+ - * / -> > >= < <= = == != ( ) { }")
    assert tipos(toks) == [T.SUMA, T.RESTA, T.MULTIPLICACION, T.DIVISION, T.FLECHA,
                           T.MAYOR, T.MAYOR_IGUAL, T.MENOR, T.MENOR_IGUAL, T.ASIGNACION,
                           T.IGUAL, T.DIFERENTE, T.PAREN_IZQ, T.PAREN_DER,
                           T.LLAVE_IZQ, T.LLAVE_DER, T.EOF]
    assert errs == []
    toks, _ = escanear("a>=b->c==d-e")
    assert tipos(toks) == [T.ID, T.MAYOR_IGUAL, T.ID, T.FLECHA, T.ID, T.IGUAL, T.ID,
                           T.RESTA, T.ID, T.EOF]

def test_reservadas():
    toks, _ = escanear("SI si SINO Y y NO VERDADERO FALSO _x x_1 SINOX")
    assert tipos(toks) == [T.SI, T.ID, T.SINO, T.Y, T.ID, T.NO, T.VERDADERO, T.FALSO,
                           T.ID, T.ID, T.ID, T.EOF]
    assert toks[6].literal is True and toks[7].literal is False

def test_literales():
    toks, errs = escanear('18 60.5 007 "Modo noche" ""')
    assert [(t.type, t.literal) for t in toks[:-1]] == [
        (T.ENTERO, 18), (T.FLOTANTE, 60.5), (T.ENTERO, 7),
        (T.CADENA, "Modo noche"), (T.CADENA, "")]
    assert toks[3].value == '"Modo noche"'
    assert errs == []
    toks, _ = escanear("-5")
    assert tipos(toks) == [T.RESTA, T.ENTERO, T.EOF]

def test_comentarios():
    toks, errs = escanear("a // comentario -> 5 \"x\nb/c\n// al final sin salto")
    assert tvl(toks) == [(T.ID, "a"), (T.ID, "b"), (T.DIVISION, "/"), (T.ID, "c")]
    assert toks[1].linea == 2 and toks[-1].linea == 3
    assert errs == []

def test_linea_columna():
    toks, _ = escanear("x\n  y\n\tz\r\nw")
    assert [(t.value, t.linea, t.columna) for t in toks[:-1]] == [
        ("x", 1, 1), ("y", 2, 3), ("z", 3, 2), ("w", 4, 1)]

def test_errores():
    casos = {
        "@":              ([], [("E1", "@")]),
        "año":            ([(T.ID, "a"), (T.ID, "o")], [("E1", "ñ")]),
        ".5":             ([(T.ENTERO, "5")], [("E1", ".")]),
        "2clima = 3":     ([(T.ASIGNACION, "="), (T.ENTERO, "3")], [("E2", "2clima")]),
        "60.5abc":        ([], [("E2", "60.5abc")]),
        "18. x":          ([(T.ID, "x")], [("E3", "18.")]),
        "18.a":           ([(T.ID, "a")], [("E3", "18.")]),
        '"Modo noche\nx': ([(T.ID, "x")], [("E4", '"Modo noche')]),
        '"abc':           ([], [("E4", '"abc')]),
        "a ! b":          ([(T.ID, "a"), (T.ID, "b")], [("E5", "!")]),
        "a!=b":           ([(T.ID, "a"), (T.DIFERENTE, "!="), (T.ID, "b")], []),
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
    T.CADENA: ['"Modo noche"', '""', '"a b c -> // x"'],
    T.SI: ["SI"], T.SINO: ["SINO"], T.Y: ["Y"], T.FALSO: ["FALSO"],
    T.SUMA: ["+"], T.RESTA: ["-"], T.MULTIPLICACION: ["*"], T.DIVISION: ["/"],
    T.MAYOR: [">"], T.MAYOR_IGUAL: [">="], T.MENOR: ["<"], T.MENOR_IGUAL: ["<="],
    T.ASIGNACION: ["="], T.IGUAL: ["=="], T.DIFERENTE: ["!="], T.FLECHA: ["->"],
    T.LLAVE_IZQ: ["{"], T.LLAVE_DER: ["}"], T.PAREN_IZQ: ["("], T.PAREN_DER: [")"],
}
SEPARADORES = [" ", "  ", "\n", "\t", " // comentario\n", "\r\n"]

def test_buffer_aleatorio():
    rnd = random.Random(2026)
    for _ in range(300):
        esperado, partes = [], []
        for _ in range(rnd.randint(0, 40)):
            tipo = rnd.choice(list(LEXEMAS))
            lex = rnd.choice(LEXEMAS[tipo])
            esperado.append((tipo, lex))
            partes.append(lex)
            partes.append(rnd.choice(SEPARADORES))
        fuente = "".join(partes)
        for n in TAMANOS_BUFFER:
            toks, errs = escanear(fuente, n)
            assert tvl(toks) == esperado, (n, fuente)
            assert errs == [], (n, fuente, errores(errs))
            for t in toks[:-1]:
                assert fuente[t.posicion:t.posicion + len(t.value)] == t.value

def test_cargas_del_buffer():
    fuente = "a " * 50
    s = Scanner(fuente, buffer_size=8)
    s.scan_tokens()
    assert s.buffer.cargas == 13

if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK — {len(pruebas)} pruebas pasaron")
