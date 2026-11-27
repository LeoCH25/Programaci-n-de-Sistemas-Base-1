"""Salida por consola: listado de tokens, estadisticas y resumen de errores."""
from collections import Counter
from typing import List
from homescript.analizador import Resultado
from homescript.lexico.tokens import Token
from homescript.errores.error_handler import ErrorHandler
from homescript.errores.error_types import FaseError

SEPARADOR = "=" * 78

def errores_por_fase(eh: ErrorHandler) -> str:
    if not eh.errores:
        return "0"
    por_fase = Counter(e.error_codigo.fase for e in eh.errores)
    partes = [f"{fase.value} {por_fase[fase]}" for fase in FaseError if por_fase[fase]]
    return f"{len(eh.errores)} ({', '.join(partes)})"

def codigos_de_error(eh: ErrorHandler) -> str:
    cuenta = Counter(e.error_codigo.codigo for e in eh.errores)
    return " ".join(c if n == 1 else f"{c}×{n}" for c, n in cuenta.items())

def imprimir_tokens(tokens: List[Token]):
    print(f"\n=== TOKENS GENERADOS ({len(tokens)}) ===")
    print(f"{'#':>4}  {'TIPO':<15} {'LEXEMA':<20} {'LÍN':>4} {'COL':>4}  {'CATEGORÍA':<23} LITERAL")
    for i, t in enumerate(tokens, 1):
        literal = "" if t.literal is None else repr(t.literal)
        print(f"{i:>4}  {t.type.name:<15} {t.value!r:<20} {t.linea:>4} {t.columna:>4}  "
              f"{t.categoria():<23} {literal}".rstrip())

def imprimir_estadisticas(r: Resultado):
    eh = r.error_handler
    print("\n=== ESTADÍSTICAS ===")
    print(f"Tokens:        {len(r.tokens)} (incluye EOF) · cargas del buffer: {r.cargas_buffer}")
    for categoria, n in Counter(t.categoria() for t in r.tokens if not t.is_eof()).most_common():
        print(f"  {categoria:<25}{n:>4}")
    tipos = Counter(s.tipo.value for s in r.tabla)
    detalle = ", ".join(f"{n} {tipo}" for tipo, n in tipos.items())
    print(f"Símbolos:      {len(r.tabla)}" + (f" ({detalle})" if detalle else ""))
    print(f"Errores:       {errores_por_fase(eh)}" + (f" · {codigos_de_error(eh)}" if eh.errores else ""))
    print(f"Advertencias:  {eh.get_warning_count()}")
