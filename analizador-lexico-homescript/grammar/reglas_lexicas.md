# Reglas léxicas de HomeScript

Este documento reúne las reglas léxicas del lenguaje en tres formas equivalentes:

1. **Expresiones regulares** por categoría de token (sección 1).
2. **Autómata finito determinista (AFD)** de 15 estados, implementado a mano en `src/lexer.py` (sección 3; diagrama en `docs/diagrama_automata.png`, fuente en `afd_homescript.dot`).
3. **Especificación para Flex** en `homescript.l`; `lex.yy.c` es el código que Flex generó a partir de ella. `comparar_con_flex.py` verifica que el lexer en Python y el generado por Flex den los mismos tokens y errores.

Definiciones auxiliares: `letra → [A-Za-z]` · `digito → [0-9]` · `no_ascii →` cualquier carácter fuera de ASCII (ñ, á, ó, €…)

## 1. Tokens y expresiones regulares

| Categoría (salida) | Tipos de token | Expresión regular | Ejemplos |
|---|---|---|---|
| PALABRA_RESERVADA | `DISPOSITIVO SENSOR PARAMETRO SI SINO MIENTRAS ENCENDER APAGAR ESTADO CUANDO Y O NO VERDADERO FALSO` | `DISPOSITIVO \| SENSOR \| … \| FALSO` (en mayúsculas) | `SI`, `MIENTRAS`, `Y` |
| IDENTIFICADOR | `ID` | `(letra \| _)(letra \| digito \| _)*` | `clima`, `humedad_max`, `variable1`, `Noche` |
| NUMERO_ENTERO | `ENTERO` | `digito+` | `18`, `0`, `500` |
| NUMERO_FLOTANTE | `FLOTANTE` | `digito+ \. digito+` | `60.5`, `0.0` |
| CADENA | `CADENA` | `" [^"\n]* "` | `"Modo noche"` |
| OPERADOR | `SUMA RESTA MULTIPLICACION DIVISION` | `\+ \| - \| \* \| /` | `+` `-` `*` `/` |
| OPERADOR | `MAYOR MENOR MAYOR_IGUAL MENOR_IGUAL IGUAL DIFERENTE` | `> \| < \| >= \| <= \| == \| !=` | `>=` |
| OPERADOR | `ASIGNACION`, `FLECHA` | `=` , `->` | `PARAMETRO frio = 18`, `-> Frio` |
| DELIMITADOR | `LLAVE_IZQ LLAVE_DER PAREN_IZQ PAREN_DER` | `\{ \| \} \| \( \| \)` | `{` `}` `(` `)` |
| (se descarta) | comentario | `// [^\n]*` | `// enciende el clima` |
| (se descarta) | espacios | `( ' ' \| \t \| \r \| \n )+` | |

**Reglas de desempate**

1. **Lexema más largo:** `>=` gana sobre `>`, `->` sobre `-`, `//` (comentario) sobre `/`; `SINO` es una sola palabra y `SINOX` es un identificador.
2. **Palabra reservada sobre identificador:** el lexema se reconoce con el patrón de identificador y luego se busca en `PALABRAS_RESERVADAS`; si está, se reclasifica como palabra reservada.
3. **Mayúsculas y minúsculas importan:** `SI` es reservada, `si` es un identificador.

## 2. Errores léxicos

| Código | Error | Expresión que lo detecta | Ejemplo | Mensaje |
|---|---|---|---|---|
| E1 | Símbolo desconocido | cualquier carácter que no inicia ningún token | `$`, `;`, `&`, `.5` | `Símbolo desconocido '$' detectado.` |
| E2 | Identificador que empieza con dígito (o número con letras) | `digito+ (\. digito+)? (letra \| _ \| no_ascii)(letra \| digito \| _ \| no_ascii)*` | `123abc`, `0x1F`, `60.5abc` | `Identificador inválido '123abc': no puede empezar con un dígito.` |
| E3 | Flotante mal formado | `digito+ \.` (sin dígitos después) | `18.` | `Número mal formado '18.': falta al menos un dígito después del punto.` |
| E4 | Cadena sin cerrar | `" [^"\n]*` (llega al fin de línea o de archivo) | `"Frio` | `Cadena sin cerrar '"Frio': falta la comilla de cierre en la misma línea.` |
| E5 | `!` sin `=` | `!` no seguido de `=` | `a ! b` | `Símbolo desconocido '!' detectado: el operador de diferencia se escribe '!='.` |
| E6 | Identificador con carácter no permitido | identificador con un carácter no ASCII, o símbolo desconocido pegado a letras | `@var`, `#define`, `calefacción`, `año` | `Identificador inválido '@var': contiene el carácter no permitido '@'.` |

Después de cada error el lexer **sigue analizando** el resto del archivo. Los símbolos más comunes de C/Arduino llevan una pista en el mensaje (`;`, `,`, `'`, `&`, `|`, `.`, `#`).

## 3. Tabla de transición del AFD

`qN` = ir al estado · `✔ TOKEN` = aceptar y emitir · `✖ En` = error léxico · `*` = retroceder un carácter · celda vacía = se aplica la columna **otro**.

| Estado | letra / `_` | dígito | no ASCII | `.` | `"` | `/` | `-` `>` `<` `=` `!` | `+ * { } ( )` | espacio, `\t`, `\r` | `\n` | EOF | otro (`$ @ # ;`…) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **→q0** inicio | q1 | q2 | q13 | q14 | q5 | q6 | q8 … q12 | ✔ símbolo | q0 | q0 | ✔ EOF | q14 |
| **q1** identificador | q1 | q1 | q13 | | | | | | | | | ✔ ID o reservada * |
| **q2** entero | ✖ E2 | q2 | ✖ E2 | q3 | | | | | | | | ✔ ENTERO * |
| **q3** entero + `.` | | q4 | | | | | | | | | | ✖ E3 * |
| **q4** flotante | ✖ E2 | q4 | ✖ E2 | | | | | | | | | ✔ FLOTANTE * |
| **q5** cadena | q5 | q5 | q5 | q5 | ✔ CADENA | q5 | q5 | q5 | q5 | ✖ E4 * | ✖ E4 * | q5 |
| **q6** leyó `/` | | | | | | q7 | | | | | | ✔ DIVISION * |
| **q7** comentario | q7 | q7 | q7 | q7 | q7 | q7 | q7 | q7 | q7 | q0 * | q0 * | q7 |
| **q8** leyó `-` | | | | | | | `>`: ✔ FLECHA | | | | | ✔ RESTA * |
| **q9** leyó `>` | | | | | | | `=`: ✔ MAYOR_IGUAL | | | | | ✔ MAYOR * |
| **q10** leyó `<` | | | | | | | `=`: ✔ MENOR_IGUAL | | | | | ✔ MENOR * |
| **q11** leyó `=` | | | | | | | `=`: ✔ IGUAL | | | | | ✔ ASIGNACION * |
| **q12** leyó `!` | | | | | | | `=`: ✔ DIFERENTE | | | | | ✖ E5 * |
| **q13** identificador inválido | q13 | q13 | q13 | | | | | | | | | ✖ E6 * |
| **q14** símbolo desconocido | q13 (excepto `'`) | | q13 | | | | | | | | | ✖ E1 * |

En q2 y q4 los errores E2 consumen el resto de la palabra para reportarla completa (`123abc`, no solo `123`). En q13, si el lexema es un solo carácter no ASCII (por ejemplo `€` suelto), se reporta como E1.

## 4. Traza de ejemplo

Entrada: `humedad >= 60.5`

| Lee | Estado | Acción |
|---|---|---|
| `h…d` | q0 → q1 → q1… | va juntando el identificador |
| espacio | q1 | otro → ✔ ID `humedad` (retrocede: el espacio no es parte) |
| espacio | q0 | se descarta |
| `>` | q0 → q9 | espera ver si sigue `=` |
| `=` | q9 | ✔ MAYOR_IGUAL `>=` |
| `6` `0` | q0 → q2 → q2 | entero hasta ahora |
| `.` | q2 → q3 | puede ser flotante |
| `5` | q3 → q4 | ya es flotante |
| EOF | q4 | otro → ✔ FLOTANTE `60.5` (retrocede) |
| EOF | q0 | ✔ EOF |

Resultado: `(IDENTIFICADOR, "humedad")`, `(OPERADOR, ">=")`, `(NUMERO_FLOTANTE, "60.5")`.
