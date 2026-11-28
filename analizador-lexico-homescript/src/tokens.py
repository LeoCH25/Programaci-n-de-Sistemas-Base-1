"""tokens.py - Definición de tokens y palabras reservadas de HomeScript.

Contiene:
  * TokenType: los 36 tipos de token que reconoce el analizador léxico.
  * PALABRAS_RESERVADAS: tabla para reclasificar un identificador como palabra
    reservada (primero se reconoce el patrón de identificador y luego se busca
    el lexema en esta tabla).
  * SIMBOLOS_SIMPLES / SIMBOLOS_DOBLES: operadores y delimitadores de 1 y 2
    caracteres.
  * Categorías generales (formato de salida de la especificación):
    PALABRA_RESERVADA, IDENTIFICADOR, NUMERO_ENTERO, NUMERO_FLOTANTE, CADENA,
    OPERADOR y DELIMITADOR.
  * Token: la unidad léxica que produce el lexer.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    """Tipo específico de cada token (uno por palabra reservada y por símbolo)."""
    # Palabras reservadas: declaración
    DISPOSITIVO = auto()
    SENSOR = auto()
    PARAMETRO = auto()
    # Palabras reservadas: control de flujo
    SI = auto()
    SINO = auto()
    MIENTRAS = auto()
    # Palabras reservadas: comandos de hardware
    ENCENDER = auto()
    APAGAR = auto()
    # Palabras reservadas: máquinas de estado
    ESTADO = auto()
    CUANDO = auto()
    # Palabras reservadas que funcionan como operadores lógicos
    Y = auto()
    O = auto()
    NO = auto()
    # Palabras reservadas que son literales booleanos
    VERDADERO = auto()
    FALSO = auto()

    # Identificador: nombre de dispositivo, sensor, parámetro o estado
    ID = auto()

    # Literales
    ENTERO = auto()      # 18
    FLOTANTE = auto()    # 60.5
    CADENA = auto()      # "Modo noche"

    # Operadores aritméticos
    SUMA = auto()            # +
    RESTA = auto()           # -
    MULTIPLICACION = auto()  # *
    DIVISION = auto()        # /

    # Operadores relacionales
    MAYOR = auto()        # >
    MENOR = auto()        # <
    MAYOR_IGUAL = auto()  # >=
    MENOR_IGUAL = auto()  # <=
    IGUAL = auto()        # ==
    DIFERENTE = auto()    # !=

    # Asignación y flecha de transición
    ASIGNACION = auto()  # =
    FLECHA = auto()      # ->

    # Delimitadores
    LLAVE_IZQ = auto()  # {
    LLAVE_DER = auto()  # }
    PAREN_IZQ = auto()  # (
    PAREN_DER = auto()  # )

    # Fin del archivo
    EOF = auto()


# Lexema exacto (en mayúsculas) -> tipo de token. Si un identificador coincide
# con una de estas llaves, se reclasifica como palabra reservada.
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

# Símbolos que siempre son un token de un solo carácter.
SIMBOLOS_SIMPLES = {
    "+": TokenType.SUMA,
    "*": TokenType.MULTIPLICACION,
    "{": TokenType.LLAVE_IZQ,
    "}": TokenType.LLAVE_DER,
    "(": TokenType.PAREN_IZQ,
    ")": TokenType.PAREN_DER,
}

# Símbolos que pueden formar un operador de dos caracteres.
# primer carácter -> (segundo carácter, tipo si son dos, tipo si es solo uno)
# None = el carácter solo no es un token válido ('!' únicamente existe en '!=').
SIMBOLOS_DOBLES = {
    "-": (">", TokenType.FLECHA, TokenType.RESTA),
    ">": ("=", TokenType.MAYOR_IGUAL, TokenType.MAYOR),
    "<": ("=", TokenType.MENOR_IGUAL, TokenType.MENOR),
    "=": ("=", TokenType.IGUAL, TokenType.ASIGNACION),
    "!": ("=", TokenType.DIFERENTE, None),
}

# Tipos que representan un valor literal (se guardan convertidos en Token.literal).
LITERALES = {TokenType.ENTERO, TokenType.FLOTANTE, TokenType.CADENA,
             TokenType.VERDADERO, TokenType.FALSO}

_RESERVADAS = set(PALABRAS_RESERVADAS.values())
_LOGICOS = {TokenType.Y, TokenType.O, TokenType.NO}
_BOOLEANOS = {TokenType.VERDADERO, TokenType.FALSO}
_ARITMETICOS = {TokenType.SUMA, TokenType.RESTA, TokenType.MULTIPLICACION, TokenType.DIVISION}
_RELACIONALES = {TokenType.MAYOR, TokenType.MENOR, TokenType.MAYOR_IGUAL,
                 TokenType.MENOR_IGUAL, TokenType.IGUAL, TokenType.DIFERENTE}
_DELIMITADORES = {TokenType.LLAVE_IZQ, TokenType.LLAVE_DER,
                  TokenType.PAREN_IZQ, TokenType.PAREN_DER}


def categoria_general(tipo: TokenType) -> str:
    """Categoría que se imprime en la 'Lista de tokens' (formato de la especificación)."""
    if tipo in _RESERVADAS:
        return "PALABRA_RESERVADA"
    if tipo == TokenType.ID:
        return "IDENTIFICADOR"
    if tipo == TokenType.ENTERO:
        return "NUMERO_ENTERO"
    if tipo == TokenType.FLOTANTE:
        return "NUMERO_FLOTANTE"
    if tipo == TokenType.CADENA:
        return "CADENA"
    if tipo in _DELIMITADORES:
        return "DELIMITADOR"
    if tipo == TokenType.EOF:
        return "FIN_DE_ARCHIVO"
    return "OPERADOR"  # aritméticos, relacionales, '=' y '->'


def descripcion(tipo: TokenType) -> str:
    """Descripción más fina del token (se muestra en el modo --detalle)."""
    if tipo in _LOGICOS:
        return "Operador lógico (reservada)"
    if tipo in _BOOLEANOS:
        return "Booleano (reservada)"
    if tipo in _RESERVADAS:
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


@dataclass
class Token:
    """Unidad léxica reconocida por el lexer.

    type     tipo específico (TokenType)
    value    lexema tal como aparece en el archivo
    linea    línea donde empieza (desde 1)
    columna  columna donde empieza (desde 1)
    posicion índice del primer carácter dentro del archivo (desde 0)
    literal  valor convertido: int, float, str (sin comillas) o bool
    """
    type: TokenType
    value: str
    linea: int
    columna: int = 1
    posicion: int = 0
    literal: Any = None

    def __str__(self) -> str:
        return f"({self.categoria()}, \"{self.texto()}\")"

    def categoria(self) -> str:
        return categoria_general(self.type)

    def descripcion(self) -> str:
        return descripcion(self.type)

    def texto(self) -> str:
        """Lexema para mostrar: las cadenas se muestran sin sus comillas."""
        if self.type == TokenType.CADENA:
            return self.literal
        return self.value

    def is_eof(self) -> bool:
        return self.type == TokenType.EOF

    def is_identifier(self) -> bool:
        return self.type == TokenType.ID

    def is_reserved(self) -> bool:
        return self.type in _RESERVADAS

    def is_literal(self) -> bool:
        return self.type in LITERALES
