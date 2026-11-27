"""Buffer doble con centinelas usado por el analizador lexico.

El codigo fuente se carga por mitades de tamano N; cada mitad termina con un
centinela EOF que indica cuando hay que recargar la otra mitad.
"""

EOF = '\0'

class BufferManager:
    EOF_SENTINEL = EOF

    def __init__(self, source_code: str, buffer_size: int = 4096, verbose: bool = False):
        self.source = source_code
        self.N = buffer_size
        self.buffer = [self.EOF_SENTINEL] * (2 * self.N + 2)

        self.source_ptr = 0
        self.inicio_lexema = 0
        self.avance = 0

        self.mitad_inicia_en = [None, None]
        self.cargas = 0
        self.verbose = verbose

        self._load_half(0)

    def _load_half(self, half_index: int):
        start_in_buffer = 0 if half_index == 0 else self.N + 1
        sentinel_pos = self.N if half_index == 0 else 2 * self.N + 1

        self.mitad_inicia_en[half_index] = self.source_ptr
        self.cargas += 1

        chars_read = 0
        for i in range(self.N):
            if self.source_ptr < len(self.source):
                self.buffer[start_in_buffer + i] = self.source[self.source_ptr]
                self.source_ptr += 1
                chars_read += 1
            else:
                self.buffer[start_in_buffer + i] = self.EOF_SENTINEL
        self.buffer[sentinel_pos] = self.EOF_SENTINEL

        if self.verbose:
            print(f"  [I/O Disco] Cargada mitad {half_index} ({chars_read} caracteres)")

    def get_next_char(self) -> str:
        char = self.buffer[self.avance]
        self.avance += 1

        if char == self.EOF_SENTINEL:
            pos = self.avance - 1

            if pos == self.N:
                if self.mitad_inicia_en[1] != self.mitad_inicia_en[0] + self.N:
                    self._load_half(1)
                self.avance = self.N + 1
                return self.get_next_char()

            if pos == 2 * self.N + 1:
                if self.mitad_inicia_en[0] != self.mitad_inicia_en[1] + self.N:
                    self._load_half(0)
                self.avance = 0
                return self.get_next_char()

            return self.EOF_SENTINEL

        return char

    def retroceder(self):
        self.avance -= 1

    def marcar_inicio(self):
        self.inicio_lexema = self.avance