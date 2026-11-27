# Traductor HomeScript (PSB1): análisis léxico y tabla de símbolos

## Estructura del proyecto

```
codigo_lexico/
└── codigo/
    ├── main.py                      Punto de entrada (línea de comandos)
    ├── homescript/                  Paquete con el código del traductor
    │   ├── config.py                Rutas del proyecto (carpeta pruebas/, ejemplo por omisión)
    │   ├── analizador.py            Orquesta Scanner -> tokens -> tabla de símbolos (Resultado, analizar)
    │   ├── lexico/                  Análisis léxico
    │   │   ├── token_types.py       TokenType, palabras reservadas, símbolos y categorías
    │   │   ├── tokens.py            Clase Token
    │   │   ├── buffer.py            BufferManager (buffer doble con centinelas)
    │   │   └── scanner.py           Scanner (autómata de estados)
    │   ├── tabla_simbolos/
    │   │   └── symbol_table.py      SymbolTable, Simbolo, Categoria, TipoDato, funcion_hash
    │   ├── errores/
    │   │   ├── error_types.py       Catálogo de códigos de error (E1-E5, S00x, E00x)
    │   │   ├── error_handler.py     ErrorHandler (acumula errores y advertencias)
    │   │   └── error_reporter.py    ErrorReporter (contexto y puntero ^~~)
    │   ├── presentacion/
    │   │   └── consola.py           Impresión de tokens, estadísticas y resúmenes
    │   └── utilidades/
    │       └── archivos.py          Lectura de archivos fuente (UTF-8 / UTF-16 / Latin-1)
    ├── pruebas/                     Programas HomeScript de ejemplo (*.txt, banco de pruebas)
    └── tests/                       Pruebas automáticas
        ├── ejecutar_pruebas.py      Ejecuta todas las pruebas sin pytest
        ├── test_errores.py
        ├── test_main.py
        ├── test_scanner.py
        └── test_tabla_simbolos.py
```

## Uso

Todos los comandos se ejecutan desde la carpeta `codigo/`:

```
python main.py                          # analiza pruebas/ejemplo_pdf.txt
python main.py pruebas/operadores.txt   # analiza un archivo
python main.py declaraciones.txt --casillas
python main.py --todos                  # banco de pruebas completo
python main.py --todos --buffer 3       # cambia el tamaño de cada mitad del buffer

python -m homescript.lexico.scanner [archivo]                # solo tokens
python -m homescript.tabla_simbolos.symbol_table [archivo]   # solo tabla de símbolos
```

## Pruebas

```
python tests/ejecutar_pruebas.py        # las 39 pruebas
python tests/test_scanner.py            # un archivo de pruebas por separado
```
