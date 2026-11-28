"""errors.py - Manejo y reporte de errores léxicos de HomeScript.

Contiene:
  * Catálogo de errores (código, descripción, nivel y fase).
  * CompilerError: un error con su línea y columna.
  * ErrorHandler: junta los errores que encuentra el lexer SIN detener el
    análisis (el lexer reporta el error y sigue con el resto del archivo).
  * ErrorReporter: da formato a los errores. El formato principal es el de la
    especificación:  "Línea 1, Columna 4: Símbolo desconocido '$' detectado."

Errores léxicos:
  E1  Símbolo desconocido               $   ;   &   .5
  E2  Identificador que empieza con dígito (o número con letras)   123abc  60.5abc
  E3  Número flotante mal formado       18.
  E4  Cadena sin cerrar                 "Modo noche   (sin comilla final en la línea)
  E5  '!' sin '='                       a ! b
  E6  Identificador con carácter no permitido   @var  #define  calefacción
      (un identificador solo admite letras sin acento, dígitos y '_')
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, List, Optional

from tokens import Token


class NivelError(Enum):
    WARNING = auto()  # se informa, no cuenta como error
    ERROR = auto()    # se informa y el análisis sigue
    FATAL = auto()    # detiene el análisis


class FaseError(Enum):
    LEXICO = "Léxico"
    SINTAXIS = "Sintáctico"
    SEMANTICO = "Semántico"


@dataclass
class ErrorCode:
    codigo: str
    descripcion: str
    nivel: NivelError
    fase: FaseError


_ERROR, _LEX = NivelError.ERROR, FaseError.LEXICO

ERRORES_LEXICOS = {
    "UNKNOWN_SYMBOL":      ErrorCode("E1", "Símbolo desconocido", _ERROR, _LEX),
    "STARTS_WITH_DIGIT":   ErrorCode("E2", "Empieza con dígito", _ERROR, _LEX),
    "INVALID_FLOAT":       ErrorCode("E3", "Número flotante mal formado", _ERROR, _LEX),
    "UNTERMINATED_STRING": ErrorCode("E4", "Cadena sin cerrar", _ERROR, _LEX),
    "INVALID_OPERATOR":    ErrorCode("E5", "'!' sin '='", _ERROR, _LEX),
    "INVALID_IDENTIFIER":  ErrorCode("E6", "Carácter no permitido", _ERROR, _LEX),
}

# Errores que detecta la tabla de símbolos (módulo extra, opción --tabla).
ERRORES_TABLA = {
    "UNEXPECTED_TOKEN": ErrorCode("S001", "Token inesperado", _ERROR, FaseError.SINTAXIS),
    "MISSING_TOKEN":    ErrorCode("S002", "Falta un token", _ERROR, FaseError.SINTAXIS),
    "REDECLARED_IDENTIFIER": ErrorCode("E005", "Identificador declarado más de una vez",
                                       _ERROR, FaseError.SEMANTICO),
}

# Pistas para los símbolos desconocidos más comunes (errores típicos de C/Arduino).
PISTAS = {
    ";": "HomeScript no usa ';' para terminar instrucciones",
    ",": "los decimales se escriben con punto, p. ej. 1.5",
    "'": "las cadenas van entre comillas dobles",
    "&": "el Y lógico se escribe Y",
    "|": "el O lógico se escribe O",
    ".": "un número decimal necesita parte entera, p. ej. 0.5",
    "#": "los comentarios se escriben con //",
    "“": "usa comillas dobles normales (\")",
    "”": "usa comillas dobles normales (\")",
}


@dataclass
class CompilerError:
    error_codigo: ErrorCode
    mensaje: str
    linea: int
    columna: int
    posicion: int = 0
    token: Optional[Token] = None
    contexto: Optional[Any] = None  # lexema con el error (sirve para subrayarlo)

    def __str__(self) -> str:
        """Formato de la especificación: 'Línea L, Columna C: descripción.'"""
        return f"Línea {self.linea}, Columna {self.columna}: {self.mensaje}"

    def detalle(self) -> str:
        """Formato largo: fase y código del error."""
        return f"[{self.error_codigo.fase.value}] {self.error_codigo.codigo} · {self}"


class ErrorHandler:
    """Acumula errores y advertencias; el análisis no se detiene (salvo FATAL)."""

    def __init__(self):
        self.errores: List[CompilerError] = []
        self.warnings: List[CompilerError] = []

    @property
    def has_errores(self) -> bool:
        return bool(self.errores)

    def report(self, error_codigo: ErrorCode, mensaje: str, linea: int, columna: int,
               posicion: int = 0, token: Optional[Token] = None, contexto: Any = None):
        error = CompilerError(error_codigo, mensaje, linea, columna, posicion, token, contexto)
        if error_codigo.nivel == NivelError.WARNING:
            self.warnings.append(error)
            return
        self.errores.append(error)
        if error_codigo.nivel == NivelError.FATAL:
            raise RuntimeError(str(error))

    # ----- Errores léxicos (los llama el lexer) -----

    def report_unknown_symbol(self, simbolo: str, linea: int, columna: int, posicion: int):
        pista = PISTAS.get(simbolo)
        if pista is None and ord(simbolo) > 127:
            pista = "solo se permiten caracteres ASCII"
        extra = f" ({pista})" if pista else ""
        self.report(ERRORES_LEXICOS["UNKNOWN_SYMBOL"],
                    f"Símbolo desconocido '{simbolo}' detectado{extra}.",
                    linea, columna, posicion, contexto=simbolo)

    def report_starts_with_digit(self, texto: str, linea: int, columna: int, posicion: int):
        if "." in texto:
            mensaje = f"Número mal formado '{texto}': tiene letras pegadas."
        else:
            mensaje = f"Identificador inválido '{texto}': no puede empezar con un dígito."
        self.report(ERRORES_LEXICOS["STARTS_WITH_DIGIT"], mensaje,
                    linea, columna, posicion, contexto=texto)

    def report_invalid_float(self, texto: str, linea: int, columna: int, posicion: int):
        self.report(ERRORES_LEXICOS["INVALID_FLOAT"],
                    f"Número mal formado '{texto}': "
                    "falta al menos un dígito después del punto.",
                    linea, columna, posicion, contexto=texto)

    def report_unterminated_string(self, texto: str, linea: int, columna: int, posicion: int):
        self.report(ERRORES_LEXICOS["UNTERMINATED_STRING"],
                    f"Cadena sin cerrar '{texto}': "
                    "falta la comilla de cierre en la misma línea.",
                    linea, columna, posicion, contexto=texto)

    def report_invalid_operator(self, simbolo: str, linea: int, columna: int, posicion: int):
        self.report(ERRORES_LEXICOS["INVALID_OPERATOR"],
                    f"Símbolo desconocido '{simbolo}' detectado: "
                    "el operador de diferencia se escribe '!='.",
                    linea, columna, posicion, contexto=simbolo)

    def report_invalid_identifier(self, texto: str, invalido: str, linea: int, columna: int,
                                  posicion: int):
        self.report(ERRORES_LEXICOS["INVALID_IDENTIFIER"],
                    f"Identificador inválido '{texto}': "
                    f"contiene el carácter no permitido '{invalido}'.",
                    linea, columna, posicion, contexto=texto)

    # ----- Errores de la tabla de símbolos (módulo extra) -----

    def report_redeclaration(self, nombre: str, linea: int, columna: int,
                             categoria_anterior: str, linea_anterior: int):
        self.report(ERRORES_TABLA["REDECLARED_IDENTIFIER"],
                    f"'{nombre}' ya fue declarado como {categoria_anterior} "
                    f"en la línea {linea_anterior}.",
                    linea, columna, contexto=nombre)

    def report_signed_number(self, signo: Token, numero: Token):
        self.report(ERRORES_TABLA["UNEXPECTED_TOKEN"],
                    f"Los números no llevan signo: '-{numero.value}'.",
                    signo.linea, signo.columna, signo.posicion, token=signo,
                    contexto="-".ljust(numero.posicion - signo.posicion) + numero.value)

    def report_missing_token(self, esperado: str, encontrado: Token, despues_de: Token):
        llego = "el fin del archivo" if encontrado.is_eof() else f"'{encontrado.value}'"
        mensaje = f"Se esperaba {esperado} y llegó {llego}."
        codigo = ERRORES_TABLA["MISSING_TOKEN"]
        if encontrado.linea == despues_de.linea and not encontrado.is_eof():
            self.report(codigo, mensaje, encontrado.linea, encontrado.columna,
                        encontrado.posicion, token=encontrado, contexto=encontrado.value)
        else:  # se señala justo después del último token correcto
            largo = len(despues_de.value)
            self.report(codigo, mensaje, despues_de.linea, despues_de.columna + largo,
                        despues_de.posicion + largo, token=encontrado, contexto="")

    def get_error_count(self) -> int:
        return len(self.errores)


class ErrorReporter:
    """Da formato a la lista de errores."""

    @staticmethod
    def lista_errores(errores: List[CompilerError]) -> List[str]:
        """Un renglón por error, en el formato de la especificación."""
        return [str(e) for e in errores]

    @staticmethod
    def con_contexto(error: CompilerError, fuente: str) -> str:
        """Error en formato largo + la línea del código con '^~~~' bajo el lexema."""
        lineas = fuente.split("\n")
        if not 1 <= error.linea <= len(lineas):
            return error.detalle()
        linea = lineas[error.linea - 1].rstrip("\r")
        inicio = max(0, error.columna - 1)
        # Se copian los tabuladores para que '^' quede alineado en la consola.
        sangria = "".join("\t" if ch == "\t" else " " for ch in linea[:inicio])
        lexema = error.contexto if isinstance(error.contexto, str) else ""
        resto = linea[inicio + 1:inicio + len(lexema)]
        subrayado = "".join("\t" if ch == "\t" else "~" for ch in resto)
        return f"{error.detalle()}\n    {linea}\n    {sangria}^{subrayado}"
