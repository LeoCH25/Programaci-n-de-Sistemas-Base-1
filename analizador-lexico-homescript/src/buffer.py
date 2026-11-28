"""buffer.py - Buffer doble con centinelas para leer el código fuente.

El texto se carga por mitades de N caracteres. Al final de cada mitad hay un
centinela (EOF = '\\0'): cuando el lexer lo encuentra, se recarga la otra mitad
y la lectura sigue sin que el lexer se entere. Si el centinela aparece en otro
lugar, es el fin real del archivo.

Distribución en memoria (N = tamaño de cada mitad):
    [ mitad 0 : N caracteres ][ centinela ][ mitad 1 : N caracteres ][ centinela ]
     0 .............. N-1         N          N+1 ........... 2N          2N+1
"""

EOF = '\0'  # centinela y marca de fin de archivo


class BufferManager:
    EOF_SENTINEL = EOF

    def __init__(self, source_code: str, buffer_size: int = 4096):
        self.source = source_code
        self.N = buffer_size
        self.buffer = [self.EOF_SENTINEL] * (2 * self.N + 2)

        self.source_ptr = 0      # siguiente carácter del archivo que falta cargar
        self.inicio_lexema = 0   # dónde empezó el lexema actual
        self.avance = 0          # siguiente casilla del buffer que se va a leer

        self.mitad_inicia_en = [None, None]  # posición del archivo cargada en cada mitad
        self.cargas = 0                      # cuántas veces se cargó una mitad

        self._cargar_mitad(0)

    def _cargar_mitad(self, mitad: int):
        """Copia los siguientes N caracteres del archivo a la mitad indicada."""
        inicio = 0 if mitad == 0 else self.N + 1
        centinela = self.N if mitad == 0 else 2 * self.N + 1

        self.mitad_inicia_en[mitad] = self.source_ptr
        self.cargas += 1
        for i in range(self.N):
            if self.source_ptr < len(self.source):
                self.buffer[inicio + i] = self.source[self.source_ptr]
                self.source_ptr += 1
            else:
                self.buffer[inicio + i] = self.EOF_SENTINEL
        self.buffer[centinela] = self.EOF_SENTINEL

    def get_next_char(self) -> str:
        """Devuelve el siguiente carácter (o EOF) y avanza el puntero."""
        char = self.buffer[self.avance]
        self.avance += 1

        if char == self.EOF_SENTINEL:
            pos = self.avance - 1
            if pos == self.N:                      # centinela al final de la mitad 0
                # Solo se recarga si la mitad 1 no tiene ya lo que sigue
                # (puede tenerlo si antes se retrocedió hasta la mitad 0).
                if self.mitad_inicia_en[1] != self.mitad_inicia_en[0] + self.N:
                    self._cargar_mitad(1)
                self.avance = self.N + 1
                return self.get_next_char()
            if pos == 2 * self.N + 1:              # centinela al final de la mitad 1
                if self.mitad_inicia_en[0] != self.mitad_inicia_en[1] + self.N:
                    self._cargar_mitad(0)
                self.avance = 0
                return self.get_next_char()
            return self.EOF_SENTINEL               # fin real del archivo

        return char

    def retroceder(self):
        """Regresa un carácter (el último leído no pertenece al token)."""
        self.avance -= 1

    def marcar_inicio(self):
        """Marca el inicio de un nuevo lexema."""
        self.inicio_lexema = self.avance
