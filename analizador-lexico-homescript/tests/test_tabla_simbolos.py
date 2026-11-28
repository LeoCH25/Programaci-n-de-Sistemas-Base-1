"""Pruebas de la tabla de símbolos (módulo extra, opción --tabla).

Uso (desde la carpeta del proyecto):  python tests/test_tabla_simbolos.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from errors import ERRORES_TABLA, ErrorHandler, ErrorReporter, FaseError, NivelError
from lexer import Lexer
from tabla_simbolos import Categoria, Simbolo, SymbolTable, TAMANIO_TABLA, TipoDato, funcion_hash

D, S, P = Categoria.DISPOSITIVO, Categoria.SENSOR, Categoria.PARAMETRO
I = TipoDato.INDEFINIDO


def leer(ruta):
    return (RAIZ / "tests" / ruta).read_text(encoding="utf-8")


def tabla_de(fuente):
    eh = ErrorHandler()
    tabla = SymbolTable(eh)
    tabla.llenar(Lexer(fuente, eh).scan_tokens())
    return tabla, eh


def errores(eh):
    return [(e.error_codigo.codigo, e.linea, e.columna, e.contexto) for e in eh.errores]


def test_insertar_y_buscar():
    tabla = SymbolTable()
    assert len(tabla) == 0 and tabla.buscar("clima") is None
    clima = Simbolo("clima", D, TipoDato.ENTIDAD, linea=1, columna=13)
    assert tabla.insertar(clima) is True
    assert tabla.buscar("clima") is clima and "clima" in tabla
    assert tabla.buscar("Clima") is None                       # distingue mayúsculas
    assert tabla.insertar(Simbolo("clima", S, TipoDato.ENTIDAD, linea=4, columna=8)) is False
    assert tabla.buscar("clima").categoria == D and len(tabla) == 1
    e = tabla.error_handler.errores[0]
    assert (e.error_codigo.codigo, e.linea, e.columna, e.contexto) == ("E005", 4, 8, "clima")
    e005 = ERRORES_TABLA["REDECLARED_IDENTIFIER"]
    assert (e005.nivel, e005.fase) == (NivelError.ERROR, FaseError.SEMANTICO)


def test_funcion_hash_y_colisiones():
    assert funcion_hash("clima") == sum(map(ord, "clima")) % TAMANIO_TABLA == 13
    tabla = SymbolTable()
    for i, nombre in enumerate(["frio", "rifo", "ofri"], 1):  # mismas letras = misma casilla
        assert tabla.insertar(Simbolo(nombre, P, TipoDato.ENTERO, i, linea=i))
    assert [tabla.buscar(n).valor for n in ["frio", "rifo", "ofri"]] == [1, 2, 3]
    casilla = tabla.tabla[funcion_hash("frio")]
    assert [casilla.nombre, casilla.siguiente.nombre, casilla.siguiente.siguiente.nombre] == \
           ["ofri", "rifo", "frio"]                            # el nuevo queda al inicio
    assert [s.nombre for s in tabla] == ["frio", "rifo", "ofri"]


def test_ejemplo_especificacion():
    tabla, eh = tabla_de(leer("valid/programa1_ejemplo_especificacion.txt"))
    E = TipoDato.ENTIDAD
    assert [(s.nombre, s.categoria, s.tipo, s.valor, s.ambito, s.linea) for s in tabla] == [
        ("clima", D, E, None, "global", 1),
        ("ventilador", D, E, None, "global", 2),
        ("luces", D, E, None, "global", 3),
        ("temperatura", S, E, None, "global", 4),
        ("humedad", S, E, None, "global", 5),
        ("frio", P, TipoDato.ENTERO, 18, "global", 6),
        ("calor", P, TipoDato.ENTERO, 28, "global", 7),
        ("humedad_max", P, TipoDato.FLOTANTE, 60.5, "global", 8),
    ]
    assert eh.errores == []
    assert "Noche" not in tabla and "Frio" not in tabla


def test_declaraciones():
    tabla, eh = tabla_de(leer("valid/programa4_declaraciones.txt"))
    assert [(s.nombre, s.tipo, s.valor) for s in tabla] == [
        ("clima", TipoDato.ENTIDAD, None),
        ("temperatura", TipoDato.ENTIDAD, None),
        ("limite", TipoDato.ENTERO, 30),
        ("umbral", TipoDato.FLOTANTE, 21.5),
        ("aviso", TipoDato.CADENA, "Modo noche"),
        ("activo", TipoDato.BOOLEANO, True),
        ("frio", I, None), ("calor", I, None), ("humedad", I, None),
        ("Clima", TipoDato.ENTIDAD, None),
    ]
    assert errores(eh) == [
        ("E005", 8, 13, "clima"),
        ("E005", 9, 11, "temperatura"),
        ("S001", 10, 18, "-5"),
        ("S002", 11, 17, "28"),
        ("S002", 12, 21, "temperatura"),
        ("S002", 13, 7, ""),
    ]


def test_casos_sueltos():
    casos = {
        "PARAMETRO x = FALSO":    ([("x", TipoDato.BOOLEANO, False)], []),
        "PARAMETRO x = - 2.5":    ([("x", I, None)], [("S001", 1, 15, "- 2.5")]),
        "PARAMETRO x =":          ([("x", I, None)], [("S002", 1, 14, "")]),
        "PARAMETRO":              ([], [("S002", 1, 10, "")]),
        "DISPOSITIVO SI":         ([], [("S002", 1, 13, "SI")]),
        "ENCENDER luz":           ([], []),
        "PARAMETRO x = .5":       ([("x", I, None)], [("E1", 1, 15, ".")]),
        "PARAMETRO x = 1,5":      ([("x", I, None)], [("E1", 1, 16, ",")]),
        "PARAMETRO x = 500;":     ([("x", TipoDato.ENTERO, 500)], [("E1", 1, 18, ";")]),
    }
    for fuente, (esperado_tabla, esperado_errores) in casos.items():
        tabla, eh = tabla_de(fuente)
        assert [(s.nombre, s.tipo, s.valor) for s in tabla] == esperado_tabla, fuente
        assert errores(eh) == esperado_errores, (fuente, errores(eh))


def test_sin_errores_en_cascada():
    """Un error léxico no provoca además un error de la tabla en el mismo lugar."""
    tabla, eh = tabla_de(leer("invalid/errores1_lexicos.txt"))
    assert [e.error_codigo.codigo for e in eh.errores] == ["E6", "E2", "E3", "E1", "E5", "E4"]
    assert [(s.nombre, s.tipo) for s in tabla] == [
        ("temperatura", TipoDato.ENTIDAD), ("umbral", I), ("costo", I)]


def test_formato_de_la_tabla():
    tabla, _ = tabla_de(leer("valid/programa1_ejemplo_especificacion.txt"))
    texto = tabla.formatear()
    assert texto.startswith("=== TABLA DE SÍMBOLOS (8 símbolo(s), 101 casillas) ===")
    assert "humedad_max  PARAMETRO    flotante  60.5" in texto
    assert texto.endswith("Casillas usadas: 8 · colisiones: 0")
    assert "(vacía)" in SymbolTable().formatear()


def test_reporte_de_redeclaracion():
    fuente = "SENSOR luz\nDISPOSITIVO luz\n"
    _, eh = tabla_de(fuente)
    assert ErrorReporter.con_contexto(eh.errores[0], fuente).splitlines() == [
        "[Semántico] E005 · Línea 2, Columna 13: 'luz' ya fue declarado como SENSOR en la línea 1.",
        "    DISPOSITIVO luz",
        "                ^~~",
    ]


if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK - {len(pruebas)} pruebas pasaron")
