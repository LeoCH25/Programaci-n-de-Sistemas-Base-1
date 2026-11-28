/* ============================================================================
 * homescript.l - Reglas léxicas de HomeScript para Flex
 * ----------------------------------------------------------------------------
 * Versión "con herramienta generadora" del mismo analizador léxico que
 * src/lexer.py implementa a mano con un AFD. Reconoce los mismos 36 tipos de
 * token y reporta los mismos errores (E1-E6) con su línea y columna.
 *
 * Cómo se resuelven las ambigüedades (igual que en el AFD):
 *   - Flex siempre toma el lexema MÁS LARGO ('>=' antes que '>', 'SINOX' es ID).
 *   - Si dos reglas reconocen el mismo largo gana la que aparece PRIMERO; por
 *     eso las palabras reservadas van antes que la regla de identificador.
 *
 * Generar y compilar (Linux, macOS o MSYS2/WSL en Windows):
 *     flex -o lex.yy.c homescript.l
 *     gcc lex.yy.c -o homescript_flex
 * Usar:
 *     ./homescript_flex ../tests/valid/programa1_ejemplo_especificacion.txt
 *     ./homescript_flex -c archivo.txt   (formato crudo; lo usa comparar_con_flex.py)
 * ========================================================================== */

%option noyywrap nounput noinput 8bit

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ----- Posición: línea y columna del siguiente carácter ----- */
static int linea = 1, columna = 1;
static int linea_ini = 1, col_ini = 1;   /* inicio del token actual */

/* Se ejecuta antes de cada acción: guarda dónde empieza el lexema y avanza.
 * Los bytes de continuación UTF-8 (10xxxxxx) no cuentan como columna, así una
 * 'ó' (2 bytes) avanza una sola columna, igual que en Python. */
static void avanzar(const char *texto, int largo) {
    int i;
    linea_ini = linea;
    col_ini = columna;
    for (i = 0; i < largo; i++) {
        unsigned char c = (unsigned char) texto[i];
        if (c == '\n') { linea++; columna = 1; }
        else if ((c & 0xC0) != 0x80) columna++;
    }
}
#define YY_USER_ACTION avanzar(yytext, yyleng);

/* Mensajes de error (los mismos de src/errors.py). */
#define MSG_E1    "Símbolo desconocido '%s' detectado.%s"
#define MSG_E2_ID "Identificador inválido '%s': no puede empezar con un dígito.%s"
#define MSG_E2_NUM "Número mal formado '%s': tiene letras pegadas.%s"
#define MSG_E3    "Número mal formado '%s': falta al menos un dígito después del punto.%s"
#define MSG_E4    "Cadena sin cerrar '%s': falta la comilla de cierre en la misma línea.%s"
#define MSG_E5    "Símbolo desconocido '%s' detectado: " \
                  "el operador de diferencia se escribe '!='.%s"
#define MSG_E6    "Identificador inválido '%s': contiene el carácter no permitido '%s'."

/* ----- Listas de tokens y de errores (se imprimen al final) ----- */
typedef struct {
    const char *tipo, *categoria;
    char *lexema;
    int linea, columna;
} Token;
typedef struct {
    const char *codigo;
    char *lexema, *mensaje;
    int linea, columna;
} Error;

static Token *tokens = NULL;  static int n_tokens = 0,  cap_tokens = 0;
static Error *errores = NULL; static int n_errores = 0, cap_errores = 0;

static char *copiar(const char *s, int largo) {
    char *r = (char *) malloc(largo + 1);
    memcpy(r, s, largo);
    r[largo] = '\0';
    return r;
}

static void token(const char *tipo, const char *categoria) {
    if (n_tokens == cap_tokens) {
        cap_tokens = cap_tokens ? 2 * cap_tokens : 64;
        tokens = (Token *) realloc(tokens, cap_tokens * sizeof(Token));
    }
    tokens[n_tokens].tipo = tipo;
    tokens[n_tokens].categoria = categoria;
    tokens[n_tokens].lexema = copiar(yytext, yyleng);
    tokens[n_tokens].linea = linea_ini;
    tokens[n_tokens].columna = col_ini;
    n_tokens++;
}

static void error_lexico(const char *codigo, const char *lexema, int largo,
                         const char *formato, const char *extra) {
    char mensaje[512];
    char *lex = copiar(lexema, largo);
    if (n_errores == cap_errores) {
        cap_errores = cap_errores ? 2 * cap_errores : 16;
        errores = (Error *) realloc(errores, cap_errores * sizeof(Error));
    }
    snprintf(mensaje, sizeof mensaje, formato, lex, extra ? extra : "");
    errores[n_errores].codigo = codigo;
    errores[n_errores].lexema = lex;
    errores[n_errores].mensaje = copiar(mensaje, (int) strlen(mensaje));
    errores[n_errores].linea = linea_ini;
    errores[n_errores].columna = col_ini;
    n_errores++;
}

/* Cuántos caracteres (no bytes) tiene un texto UTF-8. */
static int caracteres(const char *s, int largo) {
    int i, n = 0;
    for (i = 0; i < largo; i++)
        if (((unsigned char) s[i] & 0xC0) != 0x80) n++;
    return n;
}

/* E6: busca el primer carácter que no es letra ASCII, dígito ni '_' (con bytes UTF-8). */
static void error_identificador_invalido(void) {
    char invalido[8] = "";
    int i, j;
    for (i = 0; i < yyleng; i++) {
        unsigned char c = (unsigned char) yytext[i];
        int valido = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                     || (c >= '0' && c <= '9') || c == '_';
        if (!valido) {
            invalido[0] = yytext[i];
            for (j = 1; i + j < yyleng && j < 6
                        && ((unsigned char) yytext[i + j] & 0xC0) == 0x80; j++)
                invalido[j] = yytext[i + j];
            invalido[j] = '\0';
            break;
        }
    }
    error_lexico("E6", yytext, yyleng, MSG_E6, invalido);
}

static void error_simbolo(void) {
    error_lexico("E1", yytext, yyleng, MSG_E1, NULL);
}
%}

LETRA     [A-Za-z]
DIGITO    [0-9]
IDCAR     [A-Za-z0-9_]
NOASCII   [\x80-\xff]
SIMBOLO   [\x01-\x08\x0b\x0c\x0e-\x1f#$%&,.:;?@\[\\\]^`|~\x7f]

%%

"//"[^\n]*                   { /* comentario: se descarta */ }
[ \t\r\n]+                   { /* espacios y saltos de línea: se descartan */ }

 /* ----- Palabras reservadas (antes que la regla de identificador) ----- */
"DISPOSITIVO"                { token("DISPOSITIVO", "PALABRA_RESERVADA"); }
"SENSOR"                     { token("SENSOR", "PALABRA_RESERVADA"); }
"PARAMETRO"                  { token("PARAMETRO", "PALABRA_RESERVADA"); }
"SI"                         { token("SI", "PALABRA_RESERVADA"); }
"SINO"                       { token("SINO", "PALABRA_RESERVADA"); }
"MIENTRAS"                   { token("MIENTRAS", "PALABRA_RESERVADA"); }
"ENCENDER"                   { token("ENCENDER", "PALABRA_RESERVADA"); }
"APAGAR"                     { token("APAGAR", "PALABRA_RESERVADA"); }
"ESTADO"                     { token("ESTADO", "PALABRA_RESERVADA"); }
"CUANDO"                     { token("CUANDO", "PALABRA_RESERVADA"); }
"Y"                          { token("Y", "PALABRA_RESERVADA"); }
"O"                          { token("O", "PALABRA_RESERVADA"); }
"NO"                         { token("NO", "PALABRA_RESERVADA"); }
"VERDADERO"                  { token("VERDADERO", "PALABRA_RESERVADA"); }
"FALSO"                      { token("FALSO", "PALABRA_RESERVADA"); }

 /* ----- Identificadores válidos e inválidos ----- */
({LETRA}|_){IDCAR}*          { token("ID", "IDENTIFICADOR"); }
 /* calefacción, año */
({LETRA}|_){IDCAR}*{NOASCII}({IDCAR}|{NOASCII})*    { error_identificador_invalido(); }
 /* @var, #define */
{SIMBOLO}({LETRA}|_|{NOASCII})({IDCAR}|{NOASCII})*  { error_identificador_invalido(); }
 /* ñame (o un carácter no ASCII suelto, como €, que es E1) */
{NOASCII}({IDCAR}|{NOASCII})* {
                                if (caracteres(yytext, yyleng) == 1) error_simbolo();
                                else error_identificador_invalido();
                             }

 /* ----- Números ----- */
{DIGITO}+                    { token("ENTERO", "NUMERO_ENTERO"); }
{DIGITO}+"."{DIGITO}+        { token("FLOTANTE", "NUMERO_FLOTANTE"); }
{DIGITO}+("."{DIGITO}+)?({LETRA}|_|{NOASCII})({IDCAR}|{NOASCII})* {
                                if (memchr(yytext, '.', yyleng))
                                    error_lexico("E2", yytext, yyleng, MSG_E2_NUM, NULL);
                                else
                                    error_lexico("E2", yytext, yyleng, MSG_E2_ID, NULL);
                             }
{DIGITO}+"."                 { error_lexico("E3", yytext, yyleng, MSG_E3, NULL); }

 /* ----- Cadenas ----- */
\"[^"\n]*\"                  { token("CADENA", "CADENA"); }
\"[^"\n]*                    {
                                int largo = yyleng;
                                if (largo > 0 && yytext[largo - 1] == '\r') largo--;
                                error_lexico("E4", yytext, largo, MSG_E4, NULL);
                             }

 /* ----- Operadores y delimitadores (Flex toma el más largo: '->' antes que '-') ----- */
"->"                         { token("FLECHA", "OPERADOR"); }
"-"                          { token("RESTA", "OPERADOR"); }
">="                         { token("MAYOR_IGUAL", "OPERADOR"); }
">"                          { token("MAYOR", "OPERADOR"); }
"<="                         { token("MENOR_IGUAL", "OPERADOR"); }
"<"                          { token("MENOR", "OPERADOR"); }
"=="                         { token("IGUAL", "OPERADOR"); }
"="                          { token("ASIGNACION", "OPERADOR"); }
"!="                         { token("DIFERENTE", "OPERADOR"); }
"!"                          { error_lexico("E5", yytext, yyleng, MSG_E5, NULL); }
"+"                          { token("SUMA", "OPERADOR"); }
"*"                          { token("MULTIPLICACION", "OPERADOR"); }
"/"                          { token("DIVISION", "OPERADOR"); }
"{"                          { token("LLAVE_IZQ", "DELIMITADOR"); }
"}"                          { token("LLAVE_DER", "DELIMITADOR"); }
"("                          { token("PAREN_IZQ", "DELIMITADOR"); }
")"                          { token("PAREN_DER", "DELIMITADOR"); }

 /* ----- Cualquier otro carácter: símbolo desconocido ----- */
{SIMBOLO}|"'"                { error_simbolo(); }
.                            { error_simbolo(); }

%%

/* Imprime un lexema; las cadenas se muestran sin sus comillas (igual que main.py). */
static void imprimir_lexema(const Token *t) {
    if (strcmp(t->tipo, "CADENA") == 0)
        printf("%.*s", (int) strlen(t->lexema) - 2, t->lexema + 1);
    else
        printf("%s", t->lexema);
}

int main(int argc, char **argv) {
    const char *ruta = NULL;
    int i, crudo = 0;
    FILE *f;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-c") == 0) crudo = 1;
        else ruta = argv[i];
    }
    if (ruta == NULL) {
        fprintf(stderr, "Uso: %s [-c] archivo.txt\n", argv[0]);
        return 1;
    }
    f = fopen(ruta, "rb");
    if (f == NULL) {
        fprintf(stderr, "No se pudo abrir '%s'\n", ruta);
        return 1;
    }
    /* Se salta el BOM de UTF-8 (lo agrega el Bloc de notas de Windows). */
    if (!(fgetc(f) == 0xEF && fgetc(f) == 0xBB && fgetc(f) == 0xBF)) rewind(f);

    yyin = f;
    yylex();
    fclose(f);

    if (crudo) {   /* una línea por token o error: TIPO/CÓDIGO línea columna lexema */
        for (i = 0; i < n_tokens; i++)
            printf("T %s %d %d %s\n", tokens[i].tipo, tokens[i].linea, tokens[i].columna,
                   tokens[i].lexema);
        for (i = 0; i < n_errores; i++)
            printf("E %s %d %d %s\n", errores[i].codigo, errores[i].linea,
                   errores[i].columna, errores[i].lexema);
        return 0;
    }

    /* Formato de la especificación (el mismo de src/main.py). */
    printf("Lista de tokens:\n");
    for (i = 0; i < n_tokens; i++) {
        printf("%d: (%s, \"", i + 1, tokens[i].categoria);
        imprimir_lexema(&tokens[i]);
        printf("\")\n");
    }
    printf("\n");
    if (n_errores == 0) {
        printf("No se encontraron errores léxicos.\n");
    } else {
        printf("Lista de errores:\n");
        for (i = 0; i < n_errores; i++)
            printf("Línea %d, Columna %d: %s\n", errores[i].linea, errores[i].columna,
                   errores[i].mensaje);
    }
    printf("\nResumen: %d tokens reconocidos, %d error%s léxico%s.\n", n_tokens, n_errores,
           n_errores == 1 ? "" : "es", n_errores == 1 ? "" : "s");
    return 0;
}
