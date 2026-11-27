"""Orquestacion del analisis: Scanner -> lista de tokens -> tabla de simbolos."""
from dataclasses import dataclass
from typing import List

from homescript.lexico.scanner import Scanner
from homescript.lexico.tokens import Token
from homescript.tabla_simbolos.symbol_table import SymbolTable
from homescript.errores.error_handler import ErrorHandler

@dataclass
class Resultado:
    fuente: str
    tokens: List[Token]
    tabla: SymbolTable
    error_handler: ErrorHandler
    cargas_buffer: int

def analizar(fuente: str, buffer_size: int = 4096) -> Resultado:
    error_handler = ErrorHandler()
    scanner = Scanner(fuente, error_handler, buffer_size=buffer_size)
    tokens = scanner.scan_tokens()
    tabla = SymbolTable(error_handler)
    tabla.llenar(tokens)
    return Resultado(fuente, tokens, tabla, error_handler, scanner.buffer.cargas)
