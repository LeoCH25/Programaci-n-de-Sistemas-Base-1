"""Tipos de token de HomeScript y tablas de palabras reservadas y simbolos."""
from enum import Enum, auto

class TokenType(Enum):
    DISPOSITIVO = auto()
    SENSOR = auto()
    PARAMETRO = auto()
    SI = auto()
    SINO = auto()
    MIENTRAS = auto()
    ENCENDER = auto()
    APAGAR = auto()
    ESTADO = auto()
    CUANDO = auto()
    Y = auto()
    O = auto()
    NO = auto()
    VERDADERO = auto()
    FALSO = auto()

    ID = auto()

    ENTERO = auto()
    FLOTANTE = auto()
    CADENA = auto()

    SUMA = auto()
    RESTA = auto()
    MULTIPLICACION = auto()
    DIVISION = auto()

    MAYOR = auto()
    MENOR = auto()
    MAYOR_IGUAL = auto()
    MENOR_IGUAL = auto()
    IGUAL = auto()
    DIFERENTE = auto()

    ASIGNACION = auto()
    FLECHA = auto()

    LLAVE_IZQ = auto()
    LLAVE_DER = auto()
    PAREN_IZQ = auto()
    PAREN_DER = auto()

    EOF = auto()


PALABRAS_RESERVADAS = {
    "DISPOSITIVO": TokenType.DISPOSITIVO,
    "SENSOR": TokenType.SENSOR,
    "PARAMETRO": TokenType.PARAMETRO,
    "SI": TokenType.SI,
    "SINO": TokenType.SINO,
    "MIENTRAS": TokenType.MIENTRAS,
    "ENCENDER": TokenType.ENCENDER,
    "APAGAR": TokenType.APAGAR,
    "ESTADO": TokenType.ESTADO,
    "CUANDO": TokenType.CUANDO,
    "Y": TokenType.Y,
    "O": TokenType.O,
    "NO": TokenType.NO,
    "VERDADERO": TokenType.VERDADERO,
    "FALSO": TokenType.FALSO,
}

SIMBOLOS_SIMPLES = {
    "+": TokenType.SUMA,
    "*": TokenType.MULTIPLICACION,
    "{": TokenType.LLAVE_IZQ,
    "}": TokenType.LLAVE_DER,
    "(": TokenType.PAREN_IZQ,
    ")": TokenType.PAREN_DER,
}

SIMBOLOS_DOBLES = {
    "-": (">", TokenType.FLECHA, TokenType.RESTA),
    ">": ("=", TokenType.MAYOR_IGUAL, TokenType.MAYOR),
    "<": ("=", TokenType.MENOR_IGUAL, TokenType.MENOR),
    "=": ("=", TokenType.IGUAL, TokenType.ASIGNACION),
    "!": ("=", TokenType.DIFERENTE, None),
}

LITERALES = {
    TokenType.ENTERO,
    TokenType.FLOTANTE,
    TokenType.CADENA,
    TokenType.VERDADERO,
    TokenType.FALSO,
}

_TIPOS_RESERVADAS = set(PALABRAS_RESERVADAS.values())
_ARITMETICOS = {TokenType.SUMA, TokenType.RESTA, TokenType.MULTIPLICACION, TokenType.DIVISION}
_RELACIONALES = {TokenType.MAYOR, TokenType.MENOR, TokenType.MAYOR_IGUAL,
                 TokenType.MENOR_IGUAL, TokenType.IGUAL, TokenType.DIFERENTE}
_DELIMITADORES = {TokenType.LLAVE_IZQ, TokenType.LLAVE_DER,
                  TokenType.PAREN_IZQ, TokenType.PAREN_DER}


def es_palabra_reservada(tipo: TokenType) -> bool:
    return tipo in _TIPOS_RESERVADAS

def categoria(tipo: TokenType) -> str:
    if tipo in (TokenType.Y, TokenType.O, TokenType.NO):
        return "Operador lógico"
    if tipo in (TokenType.VERDADERO, TokenType.FALSO):
        return "Literal booleano"
    if tipo in _TIPOS_RESERVADAS:
        return "Palabra reservada"
    if tipo == TokenType.ID:
        return "Identificador"
    if tipo == TokenType.ENTERO:
        return "Constante entera"
    if tipo == TokenType.FLOTANTE:
        return "Constante flotante"
    if tipo == TokenType.CADENA:
        return "Constante de cadena"
    if tipo in _ARITMETICOS:
        return "Operador aritmético"
    if tipo in _RELACIONALES:
        return "Operador relacional"
    if tipo == TokenType.ASIGNACION:
        return "Operador de asignación"
    if tipo == TokenType.FLECHA:
        return "Flecha de transición"
    if tipo in _DELIMITADORES:
        return "Delimitador"
    return "Fin de archivo"