"""Analizador lexico (Scanner) de HomeScript.

Implementa el automata de estados que recorre el codigo fuente caracter por
caracter (a traves de BufferManager) y produce la lista de tokens. Los errores
lexicos (E1-E5) se reportan al ErrorHandler recibido.
"""
from typing import List, Optional
from homescript.lexico.token_types import TokenType, PALABRAS_RESERVADAS, SIMBOLOS_SIMPLES, SIMBOLOS_DOBLES
from homescript.lexico.tokens import Token
from homescript.lexico.buffer import EOF, BufferManager
from homescript.errores.error_handler import ErrorHandler

# Clasificacion de caracteres 
def es_letra(c: str) -> bool:
    return 'a' <= c <= 'z' or 'A' <= c <= 'Z'

def es_digito(c: str) -> bool:
    return '0' <= c <= '9'

def es_parte_de_id(c: str) -> bool:
    return es_letra(c) or es_digito(c) or c == '_'

ESPACIOS = ' \t\r'
ESTADO_DE_SIMBOLO = {'-': 8, '>': 9, '<': 10, '=': 11, '!': 12}

class Scanner:
    def __init__(self, fuente: str, error_handler: Optional[ErrorHandler] = None, *,
                 buffer_size: int = 4096):
        self.fuente = fuente
        self.buffer = BufferManager(fuente, buffer_size)
        self.tokens: List[Token] = []

        self.error_handler = error_handler if error_handler is not None else ErrorHandler()

        self.linea = 1
        self.columna = 1
        self.posicion = 0
        self._antes = (1, 1, 0)
        self._ultimo = EOF

        self.lexema: List[str] = []
        self.linea_ini = 1
        self.col_ini = 1
        self.pos_ini = 0

    def scan_tokens(self) -> List[Token]:
        while not self.tokens or not self.tokens[-1].is_eof():
            self.scan_token()
        return self.tokens

    def scan_token(self) -> Optional[Token]:
        self._iniciar_lexema()
        estado = 0

        while True:
            c = self._leer()

            if estado == 0:
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
                    return None
                elif c == EOF:
                    return self._emitir(TokenType.EOF)
                else:
                    self.error_handler.report_unknown_char(
                        c, self.linea_ini, self.col_ini, self.pos_ini)
                    return None

            elif estado == 1:
                if not es_parte_de_id(c):
                    self._retroceder()
                    return self._emitir_id()

            elif estado == 2:
                if es_digito(c):
                    pass
                elif c == '.':
                    estado = 3
                elif es_letra(c) or c == '_':
                    return self._error_numero_pegado()
                else:
                    self._retroceder()
                    return self._emitir(TokenType.ENTERO, int(self._texto()))

            elif estado == 3:
                if es_digito(c):
                    estado = 4
                else:
                    self._retroceder()
                    self.error_handler.report_invalid_float(
                        self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
                    return None

            elif estado == 4:
                if es_digito(c):
                    pass
                elif es_letra(c) or c == '_':
                    return self._error_numero_pegado()
                else:
                    self._retroceder()
                    return self._emitir(TokenType.FLOTANTE, float(self._texto()))

            elif estado == 5:
                if c == '"':
                    return self._emitir(TokenType.CADENA, self._texto()[1:-1])
                if c == '\n' or c == EOF:
                    self._retroceder()
                    self.error_handler.report_unterminated_string(
                        self._texto().rstrip('\r'), self.linea_ini, self.col_ini, self.pos_ini)
                    return None

            elif estado == 6:
                if c == '/':
                    estado = 7
                else:
                    self._retroceder()
                    return self._emitir(TokenType.DIVISION)

            elif estado == 7:
                if c == '\n' or c == EOF:
                    self._retroceder()
                    return None

            else:
                segundo, tipo_doble, tipo_simple = SIMBOLOS_DOBLES[self.lexema[0]]
                if c == segundo:
                    return self._emitir(tipo_doble)
                self._retroceder()
                if tipo_simple is None:
                    self.error_handler.report_invalid_operator(
                        self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
                    return None
                return self._emitir(tipo_simple)

    def _leer(self) -> str:
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

    def _emitir(self, tipo: TokenType, literal=None) -> Token:
        token = Token(type=tipo, value=self._texto(), linea=self.linea_ini,
                      columna=self.col_ini, posicion=self.pos_ini, literal=literal)
        self.tokens.append(token)
        return token

    def _emitir_id(self) -> Token:
        texto = self._texto()
        tipo = PALABRAS_RESERVADAS.get(texto, TokenType.ID)
        literal = {TokenType.VERDADERO: True, TokenType.FALSO: False}.get(tipo)
        return self._emitir(tipo, literal)

    def _error_numero_pegado(self) -> None:
        while es_parte_de_id(self._leer()):
            pass
        self._retroceder()
        self.error_handler.report_number_with_letters(
            self._texto(), self.linea_ini, self.col_ini, self.pos_ini)
        return None

if __name__ == "__main__":
    import sys
    from pathlib import Path
    from homescript.errores.error_reporter import ErrorReporter
    from homescript.config import EJEMPLO

    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else EJEMPLO
    fuente = ruta.read_text(encoding="utf-8-sig")

    error_handler = ErrorHandler()
    scanner = Scanner(fuente, error_handler)
    tokens = scanner.scan_tokens()

    print(f"=== TOKENS DE {ruta.name} ===")
    print(f"{'#':>3}  {'TIPO':<15} {'LEXEMA':<18} {'LÍN':>4} {'COL':>4}  LITERAL")
    for i, t in enumerate(tokens, 1):
        lit = "" if t.literal is None else repr(t.literal)
        print(f"{i:>3}  {t.type.name:<15} {t.value!r:<18} {t.linea:>4} {t.columna:>4}  {lit}")

    ErrorReporter.print_errors(error_handler.errores, error_handler.warnings, source_code=fuente)

    print(f"{len(tokens)} tokens · {scanner.buffer.cargas} cargas del buffer")
    if error_handler.has_errores:
        print("[AVISO] El análisis léxico encontró errores.")
    else:
        print("[OK] Análisis léxico completado sin errores.")