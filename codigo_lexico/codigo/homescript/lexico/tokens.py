"""Clase Token: unidad lexica producida por el Scanner."""
from dataclasses import dataclass
from typing import Any
from homescript.lexico.token_types import TokenType, LITERALES, es_palabra_reservada, categoria

@dataclass
class Token:
    type: TokenType
    value: str
    linea: int
    columna: int = 1
    posicion: int = 0
    literal: Any = None

    def __str__(self) -> str:
        return (f"Token({self.type.name}, {self.value!r}, "
                f"linea={self.linea}, col={self.columna})")

    def __repr__(self) -> str:
        return (f"Token(type={self.type}, value={self.value!r}, literal={self.literal!r}, "
                f"linea={self.linea}, columna={self.columna}, posicion={self.posicion})")

    def __eq__(self, other) -> bool:
        if not isinstance(other, Token):
            return False
        return self.type == other.type and self.value == other.value

    def is_type(self, token_type: TokenType) -> bool:
        return self.type == token_type

    def has_value(self, expected_value: Any) -> bool:
        return self.value == expected_value

    def matches(self, token_type: TokenType, value: Any = None) -> bool:
        if value is None:
            return self.is_type(token_type)
        return self.is_type(token_type) and self.has_value(value)

    def is_identifier(self) -> bool:
        return self.is_type(TokenType.ID)

    def is_reserved(self) -> bool:
        return es_palabra_reservada(self.type)

    def is_literal(self) -> bool:
        return self.type in LITERALES

    def is_eof(self) -> bool:
        return self.is_type(TokenType.EOF)

    def categoria(self) -> str:
        return categoria(self.type)
