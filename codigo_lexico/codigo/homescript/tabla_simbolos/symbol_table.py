"""Tabla de simbolos (tabla hash con encadenamiento) de HomeScript.

Registra las declaraciones DISPOSITIVO, SENSOR y PARAMETRO encontradas en la
lista de tokens y reporta redeclaraciones y declaraciones incompletas.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator, List, Optional
from homescript.lexico.token_types import TokenType as T
from homescript.lexico.tokens import Token
from homescript.errores.error_types import FaseError
from homescript.errores.error_handler import ErrorHandler

TAMANIO_TABLA = 101
AMBITO_GLOBAL = "global"

class Categoria(Enum):
    DISPOSITIVO = "DISPOSITIVO"
    SENSOR = "SENSOR"
    PARAMETRO = "PARAMETRO"

class TipoDato(Enum):
    ENTIDAD = "entidad"
    ENTERO = "entero"
    FLOTANTE = "flotante"
    CADENA = "cadena"
    BOOLEANO = "booleano"
    INDEFINIDO = "indefinido"

TIPO_DEL_LITERAL = {
    T.ENTERO: TipoDato.ENTERO,
    T.FLOTANTE: TipoDato.FLOTANTE,
    T.CADENA: TipoDato.CADENA,
    T.VERDADERO: TipoDato.BOOLEANO,
    T.FALSO: TipoDato.BOOLEANO,
}

@dataclass
class Simbolo:
    nombre: str
    categoria: Categoria
    tipo: TipoDato
    valor: Any = None
    ambito: str = AMBITO_GLOBAL
    linea: int = 0
    columna: int = 0
    siguiente: Optional["Simbolo"] = field(default=None, repr=False, compare=False)

    def valor_texto(self) -> str:
        if self.valor is None:
            return "nulo"
        if isinstance(self.valor, bool):
            return "VERDADERO" if self.valor else "FALSO"
        if isinstance(self.valor, str):
            return f'"{self.valor}"'
        return str(self.valor)

def funcion_hash(lexema: str, tamanio: int = TAMANIO_TABLA) -> int:
    suma = 0
    for c in lexema:
        suma += ord(c)
    return suma % tamanio

class SymbolTable:
    def __init__(self, error_handler: Optional[ErrorHandler] = None, tamanio: int = TAMANIO_TABLA):
        self.tamanio = tamanio
        self.tabla: List[Optional[Simbolo]] = [None] * tamanio
        self.orden: List[Simbolo] = []
        self.error_handler = error_handler if error_handler is not None else ErrorHandler()

    def buscar(self, nombre: str) -> Optional[Simbolo]:
        actual = self.tabla[funcion_hash(nombre, self.tamanio)]
        while actual is not None:
            if actual.nombre == nombre:
                return actual
            actual = actual.siguiente
        return None

    def insertar(self, simbolo: Simbolo) -> bool:
        anterior = self.buscar(simbolo.nombre)
        if anterior is not None:
            self.error_handler.report_redeclaration(
                simbolo.nombre, simbolo.linea, simbolo.columna,
                anterior.categoria.value, anterior.linea)
            return False

        indice = funcion_hash(simbolo.nombre, self.tamanio)
        simbolo.siguiente = self.tabla[indice]
        self.tabla[indice] = simbolo
        self.orden.append(simbolo)
        return True

    def formatear(self) -> str:
        titulo = f"=== TABLA DE SÍMBOLOS ({len(self)} símbolo(s), {self.tamanio} casillas) ==="
        if not self.orden:
            return f"{titulo}\n  (vacía)"

        encabezado = ["#", "NOMBRE", "CATEGORÍA", "TIPO", "VALOR INICIAL", "ÁMBITO", "LÍNEA", "CASILLA"]
        filas = [[str(i), s.nombre, s.categoria.value, s.tipo.value, s.valor_texto(), s.ambito,
                  str(s.linea), str(funcion_hash(s.nombre, self.tamanio))]
                 for i, s in enumerate(self.orden, 1)]
        anchos = [max(len(fila[c]) for fila in [encabezado] + filas) for c in range(len(encabezado))]
        derecha = {0, 6, 7}

        def renglon(celdas):
            return "  ".join(c.rjust(a) if i in derecha else c.ljust(a)
                             for i, (c, a) in enumerate(zip(celdas, anchos))).rstrip()

        lineas = [titulo, renglon(encabezado), "  ".join("-" * a for a in anchos)]
        lineas += [renglon(f) for f in filas]
        usadas = sum(1 for casilla in self.tabla if casilla is not None)
        lineas.append(f"Casillas usadas: {usadas} · colisiones: {len(self) - usadas}")
        return "\n".join(lineas)

    def imprimir(self):
        print(self.formatear())

    def imprimir_casillas(self):
        for i in range(self.tamanio):
            actual = self.tabla[i]
            if actual is not None:
                print(f"Índice [{i}]:")
                while actual is not None:
                    print(f"  → Nombre: {actual.nombre} | Categoría: {actual.categoria.value}"
                          f" | Tipo: {actual.tipo.value} | Valor: {actual.valor_texto()}")
                    actual = actual.siguiente

    def __len__(self) -> int:
        return len(self.orden)

    def __iter__(self) -> Iterator[Simbolo]:
        return iter(self.orden)

    def __contains__(self, nombre: str) -> bool:
        return self.buscar(nombre) is not None

    def llenar(self, tokens: List[Token]):
        i = 0
        while i < len(tokens):
            tipo = tokens[i].type
            if tipo in (T.DISPOSITIVO, T.SENSOR):
                i = self.declarar_entidad(tokens, i)
            elif tipo == T.PARAMETRO:
                i = self.declarar_parametro(tokens, i)
            else:
                i += 1

    def declarar_entidad(self, tokens: List[Token], i: int) -> int:
        palabra, nombre = tokens[i], self._token(tokens, i + 1)
        if not nombre.is_identifier():
            self._falta(f"un identificador después de '{palabra.value}'", nombre, palabra)
            return i + 1
        self.insertar(Simbolo(nombre.value, Categoria[palabra.type.name], TipoDato.ENTIDAD,
                              linea=nombre.linea, columna=nombre.columna))
        return i + 2

    def declarar_parametro(self, tokens: List[Token], i: int) -> int:
        palabra, nombre = tokens[i], self._token(tokens, i + 1)
        if not nombre.is_identifier():
            self._falta("un identificador después de 'PARAMETRO'", nombre, palabra)
            return i + 1

        def indefinido():
            self.insertar(Simbolo(nombre.value, Categoria.PARAMETRO, TipoDato.INDEFINIDO,
                                  linea=nombre.linea, columna=nombre.columna))

        igual = self._token(tokens, i + 2)
        if igual.type != T.ASIGNACION:
            self._falta(f"'=' después de '{nombre.value}'", igual, nombre)
            indefinido()
            return i + 2

        valor = self._token(tokens, i + 3)
        if valor.type in TIPO_DEL_LITERAL:
            if self._valor_partido(igual, valor, self._token(tokens, i + 4)):
                indefinido()
            else:
                self.insertar(Simbolo(nombre.value, Categoria.PARAMETRO, TIPO_DEL_LITERAL[valor.type],
                                      valor.literal, linea=nombre.linea, columna=nombre.columna))
            return i + 4

        numero = self._token(tokens, i + 4)
        if (valor.type == T.RESTA and numero.type in (T.ENTERO, T.FLOTANTE)
                and numero.linea == valor.linea):
            self.error_handler.report_signed_number(valor, numero)
            indefinido()
            return i + 5

        self._falta("un valor (número, cadena, VERDADERO o FALSO) después de '='", valor, igual)
        indefinido()
        return i + 3

    @staticmethod
    def _token(tokens: List[Token], k: int) -> Token:
        return tokens[k] if k < len(tokens) else tokens[-1]

    def _falta(self, esperado: str, encontrado: Token, despues_de: Token):
        if self._errores_lexicos_entre(despues_de.posicion, encontrado.posicion):
            return
        self.error_handler.report_missing_token(esperado, encontrado, despues_de)

    def _errores_lexicos_entre(self, desde: int, hasta: int) -> List:
        return [e for e in self.error_handler.errores
                if e.error_codigo.fase == FaseError.LEXICO and desde < e.posicion < hasta]

    def _valor_partido(self, igual: Token, valor: Token, siguiente: Token) -> bool:
        if self._errores_lexicos_entre(igual.posicion, valor.posicion):
            return True
        fin = valor.posicion + len(valor.value)
        if siguiente.type not in (T.ENTERO, T.FLOTANTE):
            return False
        hueco = self._errores_lexicos_entre(fin - 1, siguiente.posicion)
        return bool(hueco) and sum(len(e.contexto) for e in hueco) == siguiente.posicion - fin

if __name__ == "__main__":
    import sys
    from pathlib import Path
    from homescript.lexico.scanner import Scanner
    from homescript.errores.error_reporter import ErrorReporter
    from homescript.config import EJEMPLO

    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else EJEMPLO
    fuente = ruta.read_text(encoding="utf-8-sig")

    error_handler = ErrorHandler()
    tokens = Scanner(fuente, error_handler).scan_tokens()
    tabla = SymbolTable(error_handler)
    tabla.llenar(tokens)

    print(f"Archivo: {ruta.name} · {len(tokens)} tokens\n")
    tabla.imprimir()
    ErrorReporter.print_errors(error_handler.errores, error_handler.warnings, source_code=fuente)
