"""Catalogo de errores del compilador (lexicos, sintacticos y semanticos)."""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Any
from homescript.lexico.tokens import Token

class NivelError(Enum):
    WARNING = auto()
    ERROR = auto()
    FATAL = auto()

class FaseError(Enum):
    LEXICO = "Léxico"
    SINTAXIS = "Sintáctico"
    SEMANTICO = "Semántico"
    RUNTIME = "Ejecución"

@dataclass
class ErrorCode:
    codigo: str
    descripcion: str
    nivel: NivelError
    fase: FaseError

ERRORES_LEXICOS = {
    "UNKNOWN_CHAR":        ErrorCode("E1", "Carácter inválido", NivelError.ERROR, FaseError.LEXICO),
    "NUMBER_WITH_LETTERS": ErrorCode("E2", "Número pegado a letras", NivelError.ERROR, FaseError.LEXICO),
    "INVALID_FLOAT":       ErrorCode("E3", "Flotante mal formado", NivelError.ERROR, FaseError.LEXICO),
    "UNTERMINATED_STRING": ErrorCode("E4", "Cadena sin cerrar", NivelError.ERROR, FaseError.LEXICO),
    "INVALID_OPERATOR":    ErrorCode("E5", "Operador '!' incompleto", NivelError.ERROR, FaseError.LEXICO),
}

ERRORES_SINTAXIS = {
    "UNEXPECTED_TOKEN": ErrorCode("S001", "Token inesperado", NivelError.ERROR, FaseError.SINTAXIS),
    "MISSING_TOKEN": ErrorCode("S002", "Token esperado no encontrado", NivelError.ERROR, FaseError.SINTAXIS),
    "INCOMPLETE_EXPRESSION": ErrorCode("S003", "Expresión incompleta", NivelError.ERROR, FaseError.SINTAXIS),
}

ERRORES_SEMANTICOS = {
    "UNDEFINED_VARIABLE": ErrorCode("E001", "Variable no definida", NivelError.ERROR, FaseError.SEMANTICO),
    "TYPE_MISMATCH": ErrorCode("E002", "Incompatibilidad de tipos", NivelError.ERROR, FaseError.SEMANTICO),
    "DIVISION_BY_ZERO": ErrorCode("E003", "División por cero", NivelError.FATAL, FaseError.SEMANTICO),
    "USE_BEFORE_INICIALIZATION": ErrorCode("E004", "Variable usada sin inicializar", NivelError.ERROR,
                                           FaseError.SEMANTICO),
    "REDECLARED_IDENTIFIER": ErrorCode("E005", "Identificador declarado más de una vez", NivelError.ERROR,
                                       FaseError.SEMANTICO),
}

@dataclass
class CompilerError:
    error_codigo: ErrorCode
    mensaje: str
    linea: int
    columna: int
    posicion: int = 0
    token: Optional[Token] = None
    contexto: Optional[Any] = None

    def __str__(self) -> str:
        return (f"[{self.error_codigo.fase.value}] Error {self.error_codigo.codigo}: "
                f"{self.mensaje} (Línea {self.linea}, Columna {self.columna})")