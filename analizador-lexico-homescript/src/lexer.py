"""lexer.py - Analizador léxico (lexer / scanner) de HomeScript.

Implementación manual de un autómata finito determinista (AFD) de 15 estados
(q0-q14). El lexer lee el código carácter por carácter a través del buffer doble
(buffer.py) y, cada vez que llega a un estado de aceptación, emite un Token.

Reglas que sigue:
  * Lexema más largo: '>=' gana sobre '>', '->' sobre '-', 'SINO' es una sola palabra.
  * Palabra reservada sobre identificador: todo lo que cumple el patrón de
    identificador se busca en PALABRAS_RESERVADAS antes de emitirse.
  * Retroceso (*): cuando el último carácter leído no pertenece al token, se
    regresa al buffer para analizarlo en el siguiente token.
  * Recuperación de errores: el error se reporta al ErrorHandler y el análisis
    sigue con el resto del archivo (no se detiene en el primer error).

Estados del AFD (la tabla completa está en grammar/reglas_lexicas.md):
  q0 inicio            q5 dentro de cadena     q10 leyó '<'
  q1 identificador     q6 leyó '/'             q11 leyó '='
  q2 entero            q7 comentario //        q12 leyó '!'
  q3 entero + '.'      q8 leyó '-'             q13 identificador inválido
  q4 flotante          q9 leyó '>'             q14 leyó un símbolo desconocido
"""
from typing import List, Optional

from buffer import EOF, BufferManager
from errors import ErrorHandler
from tokens import PALABRAS_RESERVADAS, SIMBOLOS_DOBLES, SIMBOLOS_SIMPLES, Token, TokenType


# ----- Clasificación de caracteres -----

def es_letra(c: str) -> bool:
    """Solo letras ASCII: 'ñ' y las vocales con acento NO son letras válidas."""
    return 'a' <= c <= 'z' or 'A' <= c <= 'Z'


def es_digito(c: str) -> bool:
    return '0' <= c <= '9'


def es_no_ascii(c: str) -> bool:
    """Carácter fuera de ASCII (ñ, á, ó, €, ...): nunca es válido en HomeScript."""
    return c != EOF and ord(c) > 127


def es_parte_de_id(c: str) -> bool:
    return es_letra(c) or es_digito(c) or c == '_'


def es_parte_de_id_invalido(c: str) -> bool:
    """Caracteres que siguen 'pegados' a un identificador inválido (@var, calefacción)."""
    return es_parte_de_id(c) or es_no_ascii(c)


ESPACIOS = ' \t\r'
# Primer carácter de un operador que puede ser de dos caracteres -> estado del AFD.
ESTADO_DE_SIMBOLO = {'-': 8, '>': 9, '<': 10, '=': 11, '!': 12}


class Lexer:
    """Convierte el texto de un programa HomeScript en una lista de tokens."""

    def __init__(self, fuente: str, error_handler: Optional[ErrorHandler] = None, *,
                 buffer_size: int = 4096):
        self.fuente = fuente
        self.buffer = BufferManager(fuente, buffer_size)
        self.error_handler = error_handler if error_handler is not None else ErrorHandler()
        self.tokens: List[Token] = []

        # Posición del siguiente carácter por leer.
        self.linea = 1
        self.columna = 1
        self.posicion = 0
        # Posición antes del último carácter leído (para poder retroceder).
        self._antes = (1, 1, 0)
        self._ultimo = EOF

        # Lexema en construcción y dónde empezó.
        self.lexema: List[str] = []
        self.linea_ini = 1
        self.col_ini = 1
        self.pos_ini = 0

    def scan_tokens(self) -> List[Token]:
        """Analiza todo el archivo. La lista siempre termina con el token EOF."""
        while not self.tokens or not self.tokens[-1].is_eof():
            self.scan_token()
        return self.tokens

    def scan_token(self) -> Optional[Token]:
        """Recorre el AFD desde q0 hasta emitir un token, descartar algo o reportar un error.

        Devuelve el token emitido, o None si se descartó un espacio/comentario
        o se encontró un error.
        """
        self._iniciar_lexema()
        estado = 0

        while True:
            c = self._leer()

            if estado == 0:                           # q0: inicio
                if es_letra(c) or c == '_':
                    estado = 1
                elif es_digito(c):
                    estado = 2
                elif c == '"':
                    estado = 5
                elif c == '/':
                    estado = 6
                elif c in ESTADO_DE_SIMBOLO:
                    estado = ESTADO_DE_SIMBOLO[c]
                elif c in SIMBOLOS_SIMPLES:
                    return self._emitir(SIMBOLOS_SIMPLES[c])
                elif c in ESPACIOS or c == '\n':
                    return None                       # se descarta
                elif c == EOF:
                    return self._emitir(TokenType.EOF)
                elif es_no_ascii(c):
                    estado = 13
                else:
                    estado = 14

            elif estado == 1:                         # q1: identificador
                if es_parte_de_id(c):
                    pass
                elif es_no_ascii(c):
                    estado = 13                       # p. ej. calefacción
                else:
                    self._retroceder()
                    return self._emitir_id()

            elif estado == 2:                         # q2: entero
                if es_digito(c):
                    pass
                elif c == '.':
                    estado = 3
                elif es_letra(c) or c == '_' or es_no_ascii(c):
                    return self._error_empieza_con_digito()  # p. ej. 123abc
                else:
                    self._retroceder()
                    return self._emitir(TokenType.ENTERO, int(self._texto()))

            elif estado == 3:                         # q3: leyó dígitos y '.'
                if es_digito(c):
                    estado = 4
                else:
                    self._retroceder()                # p. ej. 18.
                    self.error_handler.report_invalid_float(
                        self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
                    return None

            elif estado == 4:                         # q4: flotante
                if es_digito(c):
                    pass
                elif es_letra(c) or c == '_' or es_no_ascii(c):
                    return self._error_empieza_con_digito()  # p. ej. 60.5abc
                else:
                    self._retroceder()
                    return self._emitir(TokenType.FLOTANTE, float(self._texto()))

            elif estado == 5:                         # q5: dentro de una cadena
                if c == '"':
                    return self._emitir(TokenType.CADENA, self._texto()[1:-1])
                if c == '\n' or c == EOF:
                    self._retroceder()
                    self.error_handler.report_unterminated_string(
                        self._texto().rstrip('\r'), self.linea_ini, self.col_ini, self.pos_ini)
                    return None

            elif estado == 6:                         # q6: leyó '/'
                if c == '/':
                    estado = 7
                else:
                    self._retroceder()
                    return self._emitir(TokenType.DIVISION)

            elif estado == 7:                         # q7: comentario hasta fin de línea
                if c == '\n' or c == EOF:
                    self._retroceder()
                    return None                       # se descarta

            elif estado == 13:                        # q13: identificador inválido
                if not es_parte_de_id_invalido(c):
                    self._retroceder()
                    return self._error_identificador_invalido()

            elif estado == 14:                        # q14: símbolo desconocido
                pegado = es_letra(c) or c == '_' or es_no_ascii(c)
                if pegado and self.lexema[0] != "'":  # la comilla simple se reporta sola
                    estado = 13                       # p. ej. @var, #define
                else:
                    self._retroceder()                # símbolo suelto: $, ;, &
                    self.error_handler.report_unknown_symbol(
                        self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
                    return None

            else:                                     # q8-q12: operadores de 1 o 2 caracteres
                segundo, tipo_doble, tipo_simple = SIMBOLOS_DOBLES[self.lexema[0]]
                if c == segundo:
                    return self._emitir(tipo_doble)
                self._retroceder()
                if tipo_simple is None:               # '!' sin '='
                    self.error_handler.report_invalid_operator(
                        self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
                    return None
                return self._emitir(tipo_simple)

    # ----- Lectura y retroceso -----

    def _leer(self) -> str:
        """Lee un carácter del buffer, lo agrega al lexema y actualiza línea y columna."""
        c = self.buffer.get_next_char()
        self._antes = (self.linea, self.columna, self.posicion)
        self._ultimo = c
        if c != EOF:
            self.lexema.append(c)
            self.posicion += 1
            if c == '\n':
                self.linea += 1
                self.columna = 1
            else:
                self.columna += 1
        return c

    def _retroceder(self):
        """Devuelve al buffer el último carácter leído (no es parte del token)."""
        self.buffer.retroceder()
        self.linea, self.columna, self.posicion = self._antes
        if self._ultimo != EOF:
            self.lexema.pop()

    def _iniciar_lexema(self):
        self.buffer.marcar_inicio()
        self.lexema = []
        self.linea_ini, self.col_ini, self.pos_ini = self.linea, self.columna, self.posicion

    def _texto(self) -> str:
        return ''.join(self.lexema)

    # ----- Emisión de tokens -----

    def _emitir(self, tipo: TokenType, literal=None) -> Token:
        token = Token(type=tipo, value=self._texto(), linea=self.linea_ini,
                      columna=self.col_ini, posicion=self.pos_ini, literal=literal)
        self.tokens.append(token)
        return token

    def _emitir_id(self) -> Token:
        """Reclasifica el identificador como palabra reservada si está en la tabla."""
        texto = self._texto()
        tipo = PALABRAS_RESERVADAS.get(texto, TokenType.ID)
        literal = {TokenType.VERDADERO: True, TokenType.FALSO: False}.get(tipo)
        return self._emitir(tipo, literal)

    # ----- Errores que consumen varios caracteres -----

    def _error_empieza_con_digito(self) -> None:
        """Consume el resto de la palabra (123abc, 0x1F, 60.5abc) y la reporta completa."""
        while es_parte_de_id_invalido(self._leer()):
            pass
        self._retroceder()
        self.error_handler.report_starts_with_digit(
            self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
        return None

    def _error_identificador_invalido(self) -> None:
        texto = self._texto()
        if len(texto) == 1:  # un carácter no ASCII suelto (p. ej. '€')
            self.error_handler.report_unknown_symbol(
                texto, self.linea_ini, self.col_ini, self.pos_ini)
            return None
        invalido = next(ch for ch in texto if not es_parte_de_id(ch))
        self.error_handler.report_invalid_identifier(
            texto, invalido, self.linea_ini, self.col_ini, self.pos_ini)
        return None
