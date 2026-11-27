"""ErrorHandler: acumula los errores y advertencias detectados en cada fase."""
from typing import List, Optional, Any
from homescript.errores.error_types import (CompilerError, NivelError, ErrorCode, ERRORES_LEXICOS, ERRORES_SINTAXIS, ERRORES_SEMANTICOS)
from homescript.lexico.tokens import Token


class ErrorHandler:
    def __init__(self):
        self.errores: List[CompilerError] = []
        self.warnings: List[CompilerError] = []
        self.has_errores: bool = False
        self.has_warnings: bool = False

    def add_error(self, error: CompilerError):
        self.errores.append(error)
        self.has_errores = True
        if error.error_codigo.nivel == NivelError.FATAL:
            raise Exception(str(error))

    def add_warning(self, warning: CompilerError):
        self.warnings.append(warning)
        self.has_warnings = True

    def report(self, error_codigo: ErrorCode, mensaje: str, linea: int, columna: int,
               posicion: int = 0, token: Optional[Token] = None, contexto: Any = None):
        error = CompilerError(
            error_codigo=error_codigo,
            mensaje=mensaje,
            linea=linea,
            columna=columna,
            posicion=posicion,
            token=token,
            contexto=contexto,
        )
        if error_codigo.nivel == NivelError.WARNING:
            self.add_warning(error)
        else:
            self.add_error(error)

    def report_unknown_char(self, char: str, linea: int, columna: int, posicion: int):
        self.report(
            ERRORES_LEXICOS["UNKNOWN_CHAR"],
            f"Carácter no reconocido: '{char}'",
            linea, columna, posicion, contexto=char,
        )

    def report_number_with_letters(self, text: str, linea: int, columna: int, posicion: int):
        self.report(
            ERRORES_LEXICOS["NUMBER_WITH_LETTERS"],
            f"Número pegado a letras: '{text}' (un identificador no puede empezar con dígito)",
            linea, columna, posicion, contexto=text,
        )

    def report_invalid_float(self, text: str, linea: int, columna: int, posicion: int):
        self.report(
            ERRORES_LEXICOS["INVALID_FLOAT"],
            f"Formato numérico inválido: '{text}' (falta al menos un dígito después del punto)",
            linea, columna, posicion, contexto=text,
        )

    def report_unterminated_string(self, text: str, linea: int, columna: int, posicion: int):
        self.report(
            ERRORES_LEXICOS["UNTERMINATED_STRING"],
            "Cadena de texto sin cerrar (falta comilla de cierre en la misma línea)",
            linea, columna, posicion, contexto=text,
        )

    def report_invalid_operator(self, char: str, linea: int, columna: int, posicion: int):
        self.report(
            ERRORES_LEXICOS["INVALID_OPERATOR"],
            f"'{char}' solo no es válido; el operador es '!='",
            linea, columna, posicion, contexto=char,
        )

    def report_redeclaration(self, nombre: str, linea: int, columna: int,
                             categoria_anterior: str, linea_anterior: int):
        self.report(
            ERRORES_SEMANTICOS["REDECLARED_IDENTIFIER"],
            f"'{nombre}' ya fue declarado como {categoria_anterior} en la línea {linea_anterior}",
            linea, columna, contexto=nombre,
        )

    def report_missing_token(self, esperado: str, encontrado: Token, despues_de: Token):
        self._report_hueco(ERRORES_SINTAXIS["MISSING_TOKEN"],
                           f"Se esperaba {esperado} y llegó {self._llego(encontrado)}",
                           encontrado, despues_de)

    def report_signed_number(self, signo: Token, numero: Token):
        self.report(
            ERRORES_SINTAXIS["UNEXPECTED_TOKEN"],
            f"Los números no llevan signo: '-{numero.value}' (enteros y flotantes son sin signo)",
            signo.linea, signo.columna, signo.posicion, token=signo,
            contexto="-".ljust(numero.posicion - signo.posicion) + numero.value,
        )

    @staticmethod
    def _llego(token: Token) -> str:
        return "el fin del archivo" if token.is_eof() else f"'{token.value}'"

    def _report_hueco(self, error_codigo: ErrorCode, mensaje: str, encontrado: Token, despues_de: Token):
        if encontrado.linea == despues_de.linea and not encontrado.is_eof():
            self.report(error_codigo, mensaje,
                        encontrado.linea, encontrado.columna, encontrado.posicion,
                        token=encontrado, contexto=encontrado.value)
        else:
            largo = len(despues_de.value)
            self.report(error_codigo, mensaje,
                        despues_de.linea, despues_de.columna + largo, despues_de.posicion + largo,
                        token=encontrado, contexto="")

    def clear(self):
        self.errores.clear()
        self.warnings.clear()
        self.has_errores = False
        self.has_warnings = False

    def get_error_count(self) -> int:
        return len(self.errores)

    def get_warning_count(self) -> int:
        return len(self.warnings)
