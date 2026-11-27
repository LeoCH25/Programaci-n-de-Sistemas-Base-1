import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

CODIGO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODIGO))

from homescript.lexico.scanner import Scanner
from homescript.tabla_simbolos.symbol_table import (SymbolTable, Simbolo, Categoria, TipoDato,
                                                    funcion_hash, TAMANIO_TABLA)
from homescript.errores.error_types import ERRORES_SEMANTICOS, NivelError, FaseError
from homescript.errores.error_handler import ErrorHandler
from homescript.errores.error_reporter import ErrorReporter

D, S, P = Categoria.DISPOSITIVO, Categoria.SENSOR, Categoria.PARAMETRO

def leer(nombre):
    return (CODIGO / "pruebas" / nombre).read_text(encoding="utf-8")

def tabla_de(fuente):
    eh = ErrorHandler()
    tabla = SymbolTable(eh)
    tabla.llenar(Scanner(fuente, eh).scan_tokens())
    return tabla, eh

def filas(tabla):
    return [(s.nombre, s.categoria, s.tipo, s.valor, s.ambito, s.linea) for s in tabla]

def errores(eh):
    return [(e.error_codigo.codigo, e.linea, e.columna, e.contexto) for e in eh.errores]

def salida_de(funcion, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        funcion(*args)
    return buf.getvalue()

def test_interfaz():
    tabla = SymbolTable()
    assert len(tabla) == 0 and tabla.buscar("clima") is None
    clima = Simbolo("clima", D, TipoDato.ENTIDAD, linea=1, columna=13)
    assert tabla.insertar(clima) is True
    assert tabla.buscar("clima") is clima and "clima" in tabla
    assert tabla.buscar("Clima") is None
    assert tabla.insertar(Simbolo("clima", S, TipoDato.ENTIDAD, linea=4, columna=8)) is False
    assert tabla.buscar("clima").categoria == D and len(tabla) == 1
    e = tabla.error_handler.errores[0]
    assert (e.error_codigo.codigo, e.linea, e.columna, e.contexto) == ("E005", 4, 8, "clima")
    assert "ya fue declarado como DISPOSITIVO en la línea 1" in e.mensaje

def test_catalogo_e005():
    e = ERRORES_SEMANTICOS["REDECLARED_IDENTIFIER"]
    assert (e.codigo, e.nivel, e.fase) == ("E005", NivelError.ERROR, FaseError.SEMANTICO)

def test_funcion_hash():
    assert funcion_hash("clima") == sum(map(ord, "clima")) % TAMANIO_TABLA == 13
    assert funcion_hash("frio") == funcion_hash("rifo")

def test_colisiones():
    tabla = SymbolTable()
    for i, nombre in enumerate(["frio", "rifo", "ofri"], 1):
        assert tabla.insertar(Simbolo(nombre, P, TipoDato.ENTERO, i, linea=i))
    assert [tabla.buscar(n).valor for n in ["frio", "rifo", "ofri"]] == [1, 2, 3]
    casilla = tabla.tabla[funcion_hash("frio")]
    assert [casilla.nombre, casilla.siguiente.nombre, casilla.siguiente.siguiente.nombre] == \
           ["ofri", "rifo", "frio"]
    assert [s.nombre for s in tabla] == ["frio", "rifo", "ofri"]
    tabla, _ = tabla_de(leer("ejemplo_pdf.txt"))
    chica = SymbolTable(tamanio=1)
    for s in list(tabla):
        chica.insertar(Simbolo(s.nombre, s.categoria, s.tipo, s.valor, linea=s.linea))
    assert all(chica.buscar(s.nombre).valor == s.valor for s in tabla)
    assert "colisiones: 7" in chica.formatear()

def test_ejemplo_pdf():
    tabla, eh = tabla_de(leer("ejemplo_pdf.txt"))
    E = TipoDato.ENTIDAD
    assert filas(tabla) == [
        ("clima", D, E, None, "global", 1),
        ("ventilador", D, E, None, "global", 2),
        ("luces", D, E, None, "global", 3),
        ("temperatura", S, E, None, "global", 4),
        ("humedad", S, E, None, "global", 5),
        ("frio", P, TipoDato.ENTERO, 18, "global", 6),
        ("calor", P, TipoDato.ENTERO, 28, "global", 7),
        ("humedad_max", P, TipoDato.FLOTANTE, 60.5, "global", 8),
    ]
    assert eh.errores == [] and eh.warnings == []
    assert "Noche" not in tabla and "Frio" not in tabla

def test_declaraciones():
    tabla, eh = tabla_de(leer("declaraciones.txt"))
    I = TipoDato.INDEFINIDO
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
    assert tabla.buscar("temperatura").categoria == S
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
        "PARAMETRO x = FALSO":      ([("x", TipoDato.BOOLEANO, False)], []),
        "PARAMETRO x = - 2.5":      ([("x", TipoDato.INDEFINIDO, None)], [("S001", 1, 15, "- 2.5")]),
        "PARAMETRO x =":            ([("x", TipoDato.INDEFINIDO, None)], [("S002", 1, 14, "")]),
        "PARAMETRO":                ([], [("S002", 1, 10, "")]),
        "DISPOSITIVO SI":           ([], [("S002", 1, 13, "SI")]),
        "SENSOR DISPOSITIVO luz":   ([("luz", TipoDato.ENTIDAD, None)], [("S002", 1, 8, "DISPOSITIVO")]),
        "ENCENDER luz":             ([], []),
    }
    for fuente, (esperado_tabla, esperado_errores) in casos.items():
        tabla, eh = tabla_de(fuente)
        assert [(s.nombre, s.tipo, s.valor) for s in tabla] == esperado_tabla, fuente
        assert errores(eh) == esperado_errores, (fuente, errores(eh))
    tabla = SymbolTable()
    tabla.llenar(Scanner("PARAMETRO x").scan_tokens()[:-1])
    assert tabla.buscar("x").tipo == TipoDato.INDEFINIDO

def test_sin_cascada():
    tabla, eh = tabla_de(leer("errores_lexicos.txt"))
    assert [e.error_codigo.codigo for e in eh.errores] == ["E1", "E2", "E3", "E5", "E4"]
    assert [(s.nombre, s.tipo) for s in tabla] == [
        ("calefacci", TipoDato.ENTIDAD),
        ("temperatura", TipoDato.ENTIDAD),
        ("umbral", TipoDato.INDEFINIDO),
    ]

def test_imprimir():
    tabla, eh = tabla_de(leer("ejemplo_pdf.txt"))
    texto = salida_de(tabla.imprimir)
    assert texto.startswith("=== TABLA DE SÍMBOLOS (8 símbolo(s), 101 casillas) ===")
    assert "humedad_max  PARAMETRO    flotante  60.5" in texto
    assert texto.strip().endswith("Casillas usadas: 8 · colisiones: 0")
    casillas = salida_de(tabla.imprimir_casillas)
    assert "Índice [13]:\n  → Nombre: clima | Categoría: DISPOSITIVO | Tipo: entidad | Valor: nulo" in casillas
    assert "(vacía)" in SymbolTable().formatear()
    tabla, _ = tabla_de('PARAMETRO a = "hola"\nPARAMETRO b = VERDADERO')
    assert [s.valor_texto() for s in tabla] == ['"hola"', "VERDADERO"]

def test_reporter_redeclaracion():
    fuente = "SENSOR luz\nDISPOSITIVO luz\n"
    _, eh = tabla_de(fuente)
    texto = ErrorReporter.format_error_with_context(eh.errores[0], fuente)
    assert texto.splitlines() == [
        "[Semántico] Error E005: 'luz' ya fue declarado como SENSOR en la línea 1 (Línea 2, Columna 13)",
        "    DISPOSITIVO luz",
        "                ^~~",
    ]

if __name__ == "__main__":
    pruebas = [f for nombre, f in list(globals().items()) if nombre.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"  [OK] {prueba.__name__}")
    print(f"\nOK — {len(pruebas)} pruebas pasaron")
