"""ErrorReporter: da formato a los errores (linea de contexto y puntero ^~~)."""
from typing import List, Optional
from homescript.errores.error_types import CompilerError

class ErrorReporter:
    @staticmethod
    def format_error_with_context(error: CompilerError, source_code: str) -> str:
        lines = source_code.split('\n')
        if 1 <= error.linea <= len(lines):
            context_line = lines[error.linea - 1].rstrip('\r')
            inicio = max(0, error.columna - 1)

            prefix_chars = context_line[:inicio]
            pointer_prefix = "".join('\t' if ch == '\t' else ' ' for ch in prefix_chars)

            lexema = error.contexto if isinstance(error.contexto, str) else ""
            resto = context_line[inicio + 1:inicio + len(lexema)]
            subrayado = "".join('\t' if ch == '\t' else '~' for ch in resto)

            pointer = pointer_prefix + '^' + subrayado
            return f"{error}\n    {context_line}\n    {pointer}"
        return str(error)

    @staticmethod
    def print_errors(errores: List[CompilerError], warnings: List[CompilerError],
                     show_warnings: bool = True, source_code: Optional[str] = None):
        if errores:
            print("\n=== ERRORES ===")
            for error in errores:
                if source_code:
                    print(ErrorReporter.format_error_with_context(error, source_code))
                else:
                    print(f"  [ERROR] {error}")

        if warnings and show_warnings:
            print("\n=== ADVERTENCIAS ===")
            for warning in warnings:
                if source_code:
                    print(ErrorReporter.format_error_with_context(warning, source_code))
                else:
                    print(f"  [AVISO] {warning}")

        print(f"\nResumen: {len(errores)} error(es), {len(warnings)} advertencia(s).")

    @staticmethod
    def generate_error_report(errores: List[CompilerError], warnings: List[CompilerError]) -> str:
        report = []
        if errores:
            report.append("=== ERRORES ===")
            for error in errores:
                report.append(f"[ERROR] {error}")
        if warnings:
            report.append("\n=== ADVERTENCIAS ===")
            for warning in warnings:
                report.append(f"[WARNING] {warning}")
        report.append(f"\nTotal: {len(errores)} error(es), {len(warnings)} advertencia(s).")
        return "\n".join(report)