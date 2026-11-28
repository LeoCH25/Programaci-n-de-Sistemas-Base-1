# HomeScript — Analizador Léxico

HomeScript es un lenguaje de dominio específico (DSL) en español para automatizar dispositivos y sensores del hogar (domótica). Este proyecto implementa su **analizador léxico**: lee un programa `.txt`, lo convierte en una lista ordenada de tokens y reporta cada error léxico con su línea y columna.

## Información del Curso

- **Materia:** Programación de Sistemas de Base 1
- **Institución:** Universidad Autónoma de Tamaulipas — Facultad de Ingeniería Tampico
- **Semestre:** Agosto–diciembre 2026 · Grupo 8° K
- **Profesor:** Dr. Dante Adolfo Muñoz Quintero

## Integrantes del Equipo

| Nombre | Matrícula |
|---|---|
| Vicente Bautista Roberto Nicolás | 2223330204 |
| Chavarria Uribe Leo | 2223330145 |
| Morales Urrutia Javier Antonio | 2193273017 |
| Sánchez Morales Jesús | 2223339020 |

## Descripción del Lenguaje

Un programa HomeScript **declara** los dispositivos (salidas), sensores (entradas) y parámetros de configuración, y luego describe **reglas de comportamiento**: condiciones `SI / SINO SI / SINO`, ciclos `MIENTRAS`, comandos `ENCENDER / APAGAR` y máquinas de estado `ESTADO { CUANDO condición -> OtroEstado }`. Las condiciones combinan operadores aritméticos, relacionales y lógicos (`Y`, `O`, `NO`) con paréntesis. Las palabras reservadas van en mayúsculas, los bloques se delimitan con `{ }` y los comentarios empiezan con `//`. El traductor completo (Programación de Sistemas de Base 2) generará código C++ para Arduino.

Ejemplo de la especificación del lenguaje (`tests/valid/programa1_ejemplo_especificacion.txt`):

```
DISPOSITIVO clima
DISPOSITIVO ventilador
DISPOSITIVO luces
SENSOR temperatura
SENSOR humedad
PARAMETRO frio = 18
PARAMETRO calor = 28
PARAMETRO humedad_max = 60.5
SI temperatura >= calor Y humedad > humedad_max {
    ENCENDER clima
    ENCENDER ventilador
} SINO SI temperatura <= frio {
    APAGAR clima
    APAGAR ventilador
}
MIENTRAS temperatura > frio {
    ENCENDER luces
}
ESTADO Noche {
    CUANDO temperatura < frio -> Frio
}
```

## Tokens Reconocidos

| Categoría | Tokens | Expresión regular |
|---|---|---|
| `PALABRA_RESERVADA` | `DISPOSITIVO SENSOR PARAMETRO SI SINO MIENTRAS ENCENDER APAGAR ESTADO CUANDO Y O NO VERDADERO FALSO` | la palabra exacta, en mayúsculas |
| `IDENTIFICADOR` | `clima`, `humedad_max`, `variable1`, `Noche` | `[A-Za-z_][A-Za-z0-9_]*` |
| `NUMERO_ENTERO` | `18`, `500` | `[0-9]+` |
| `NUMERO_FLOTANTE` | `60.5`, `0.0` | `[0-9]+\.[0-9]+` |
| `CADENA` | `"Modo noche"` | `"[^"\n]*"` |
| `OPERADOR` | `+ - * /` · `> < >= <= == !=` · `=` · `->` | |
| `DELIMITADOR` | `{ } ( )` | |

Se descartan los espacios, tabuladores, saltos de línea y comentarios `// …`. Cada token conserva además su tipo específico (36 tipos: `SI`, `MAYOR_IGUAL`, `FLECHA`…), su línea y su columna.

**Errores léxicos que se detectan** (el análisis no se detiene; reporta todos):

| Código | Error | Ejemplos |
|---|---|---|
| E1 | Símbolo desconocido | `$`, `;`, `&&`, `.5` |
| E2 | Identificador que empieza con dígito (o número con letras) | `123abc`, `0x1F`, `60.5abc` |
| E3 | Número flotante mal formado | `18.` |
| E4 | Cadena sin cerrar | `"Modo noche` (sin comilla final) |
| E5 | `!` sin `=` | `a ! b` |
| E6 | Identificador con un carácter no permitido | `@var`, `#define`, `calefacción`, `año` |

Detalle completo (expresiones regulares, tabla de transición del AFD y traza): [`grammar/reglas_lexicas.md`](grammar/reglas_lexicas.md). Diagrama del autómata: [`docs/diagrama_automata.png`](docs/diagrama_automata.png).

## Cómo ejecutar

Requisito: **Python 3.7 o más nuevo**. No usa librerías externas, así que no hay que instalar nada ni compilar.

1. Descarga o clona el repositorio y entra a esta carpeta (`analizador-lexico-homescript`).
2. Analiza un programa:
   ```
   python src/main.py tests/valid/programa1_ejemplo_especificacion.txt
   ```
   (en algunas computadoras el comando es `python3` o `py`).
3. Otras opciones:

| Comando | Qué hace |
|---|---|
| `python src/main.py` | Analiza el ejemplo de la especificación |
| `python src/main.py archivo.txt` | Analiza cualquier archivo (si no lo encuentra, lo busca en `tests/valid` y `tests/invalid`) |
| `python src/main.py archivo.txt --detalle` | Tabla con tipo, línea y columna de cada token; cada error con su línea de código y `^~~~` debajo; estadísticas |
| `python src/main.py archivo.txt --tabla` | Además, la tabla de símbolos (módulo extra) |
| `python src/main.py archivo.txt --guardar` | Guarda la salida en `tests/salidas/<archivo>_salida.txt` |
| `python src/main.py --todos` | Banco de pruebas: una fila por cada programa de `tests/` |
| `python src/main.py --todos --guardar` | Regenera todas las salidas de `tests/salidas/` |
| `python tests/ejecutar_pruebas.py` | Corre las 36 pruebas automáticas |

Los archivos pueden estar en UTF-8 (con o sin BOM), UTF-16 o ANSI; el programa detecta cuál es.

**Versión con Flex (opcional).** `grammar/homescript.l` describe el mismo lexer para el generador Flex, y `grammar/lex.yy.c` es el código que Flex generó. Para compilarla se necesitan `flex` y `gcc` (Linux, macOS, WSL o MSYS2):

```
cd grammar
flex -o lex.yy.c homescript.l
gcc lex.yy.c -o homescript_flex
cd ..
python grammar/comparar_con_flex.py --aleatorios 3000
```

El último comando verifica que el lexer hecho a mano y el generado por Flex den exactamente los mismos tokens y errores en los 9 programas de prueba y en 3000 programas aleatorios.

## Ejemplos de uso

**Entrada válida** (`ejemplo.txt`):

```
SENSOR luz
PARAMETRO limite = 50.5
SI luz > limite {
    ENCENDER foco
}
```

**Salida** de `python src/main.py ejemplo.txt`:

```
Lista de tokens:
1: (PALABRA_RESERVADA, "SENSOR")
2: (IDENTIFICADOR, "luz")
3: (PALABRA_RESERVADA, "PARAMETRO")
4: (IDENTIFICADOR, "limite")
5: (OPERADOR, "=")
6: (NUMERO_FLOTANTE, "50.5")
7: (PALABRA_RESERVADA, "SI")
8: (IDENTIFICADOR, "luz")
9: (OPERADOR, ">")
10: (IDENTIFICADOR, "limite")
11: (DELIMITADOR, "{")
12: (PALABRA_RESERVADA, "ENCENDER")
13: (IDENTIFICADOR, "foco")
14: (DELIMITADOR, "}")

No se encontraron errores léxicos.

Resumen: 14 tokens reconocidos, 0 errores léxicos.
```

**Entrada con errores:**

```
SENSOR 123abc
PARAMETRO x = $ 2
```

**Salida:**

```
Lista de tokens:
1: (PALABRA_RESERVADA, "SENSOR")
2: (PALABRA_RESERVADA, "PARAMETRO")
3: (IDENTIFICADOR, "x")
4: (OPERADOR, "=")
5: (NUMERO_ENTERO, "2")

Lista de errores:
Línea 1, Columna 8: Identificador inválido '123abc': no puede empezar con un dígito.
Línea 2, Columna 15: Símbolo desconocido '$' detectado.

Resumen: 5 tokens reconocidos, 2 errores léxicos.
```

Las entradas y salidas de todos los programas de prueba están en `tests/valid/`, `tests/invalid/` y `tests/salidas/`; las capturas de la ejecución, en `capturas/`.

## Estructura del repositorio

```
analizador-lexico-homescript/
├── README.md
├── .gitignore
├── LICENSE
├── src/
│   ├── main.py            punto de entrada: lee el archivo, invoca al lexer y muestra tokens y errores
│   ├── lexer.py           lógica del analizador léxico (AFD de 15 estados, q0–q14)
│   ├── tokens.py          tipos de token, palabras reservadas, símbolos y categorías
│   ├── errors.py          catálogo de errores E1–E6, ErrorHandler y ErrorReporter
│   ├── buffer.py          buffer doble con centinelas para leer el archivo
│   └── tabla_simbolos.py  tabla de símbolos (extra, opción --tabla)
├── grammar/
│   ├── reglas_lexicas.md  expresiones regulares, tabla de transición del AFD y errores
│   ├── homescript.l       las mismas reglas léxicas para Flex
│   ├── lex.yy.c           código generado por Flex a partir de homescript.l
│   ├── comparar_con_flex.py  verifica que Python y Flex den el mismo resultado
│   └── afd_homescript.dot fuente del diagrama del autómata (Graphviz)
├── tests/
│   ├── valid/             5 programas válidos (entrada)
│   ├── invalid/           4 programas con errores léxicos (entrada)
│   ├── salidas/           salida del lexer para cada programa
│   ├── test_lexer.py, test_errores.py, test_tabla_simbolos.py, test_main.py
│   └── ejecutar_pruebas.py
├── docs/
│   ├── entregable_final.pdf   documento de demostración funcional
│   ├── entregable_final.docx  el mismo documento, editable
│   └── diagrama_automata.png
└── capturas/              captura01 … captura08 (.png)
```
