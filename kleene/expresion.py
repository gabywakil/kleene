"""Expresiones regulares: análisis sintáctico (parser) y árbol sintáctico.

Gramática (de menor a mayor precedencia):
    expresion  := termino ( 'U' termino )*        unión
    termino    := factor factor*                  concatenación
    factor     := atomo '*'*                      estrella de Kleene
    atomo      := simbolo | 'ε' | '∅' | '(' expresion ')'

Para la unión se aceptan los operadores  U  +  |  ∪
Para la palabra vacía se acepta  ε  o  λ ;  para el lenguaje vacío  ∅
"""
from __future__ import annotations

from dataclasses import dataclass

ALFABETOS = {
    "abc": ("a", "b", "c"),
    "01": ("0", "1"),
}

OPERADORES_UNION = {"U", "+", "|", "∪"}
SIMBOLOS_EPSILON = {"ε", "λ"}
SIMBOLOS_VACIO = {"∅"}


class ErrorExpresion(ValueError):
    """Error de sintaxis en la expresión regular, con la posición del problema."""

    def __init__(self, mensaje: str, posicion: int | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.posicion = posicion


# ----------------------------------------------------------------------------
# Nodos del árbol sintáctico
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Simbolo:
    c: str


@dataclass(frozen=True)
class Epsilon:
    pass


@dataclass(frozen=True)
class Vacio:
    pass


@dataclass(frozen=True)
class Caja:
    """Subexpresión genérica (R₁, R₂...). Solo se usa para dibujar las figuras base."""
    nombre: str


@dataclass(frozen=True)
class Union:
    izq: object
    der: object


@dataclass(frozen=True)
class Concat:
    izq: object
    der: object


@dataclass(frozen=True)
class Estrella:
    expr: object


# ----------------------------------------------------------------------------
# Analizador léxico
# ----------------------------------------------------------------------------
def _tokenizar(texto: str, alfabeto) -> list[tuple[str, str, int]]:
    tokens = []
    for i, ch in enumerate(texto):
        if ch.isspace() or ch in ".·":          # el punto de concatenación es opcional
            continue
        if ch in OPERADORES_UNION:
            tokens.append(("U", ch, i))
        elif ch == "*":
            tokens.append(("*", ch, i))
        elif ch in "()":
            tokens.append((ch, ch, i))
        elif ch in SIMBOLOS_EPSILON:
            tokens.append(("EPS", ch, i))
        elif ch in SIMBOLOS_VACIO:
            tokens.append(("VACIO", ch, i))
        elif ch in alfabeto:
            tokens.append(("SIM", ch, i))
        else:
            raise ErrorExpresion(
                f"El símbolo '{ch}' (posición {i + 1}) no pertenece al alfabeto "
                f"{{{', '.join(alfabeto)}}}.", i)
    return tokens


# ----------------------------------------------------------------------------
# Analizador sintáctico (descenso recursivo)
# ----------------------------------------------------------------------------
class Parser:
    INICIO_ATOMO = ("SIM", "EPS", "VACIO", "(")

    def __init__(self, tokens, texto):
        self.tokens = tokens
        self.texto = texto
        self.i = 0

    def _ver(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _avanzar(self):
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def _pos_actual(self):
        tok = self._ver()
        return tok[2] if tok else len(self.texto)

    def analizar(self):
        if not self.tokens:
            raise ErrorExpresion("La expresión está vacía. Escribe algo como (a U b)*abc.", 0)
        nodo = self._expresion()
        tok = self._ver()
        if tok is not None:
            raise ErrorExpresion(f"Símbolo inesperado '{tok[1]}' en la posición {tok[2] + 1}"
                                 + (" (¿sobra un paréntesis de cierre?)." if tok[0] == ")" else "."),
                                 tok[2])
        return nodo

    def _expresion(self):
        nodo = self._termino()
        while (tok := self._ver()) is not None and tok[0] == "U":
            self._avanzar()
            nodo = Union(nodo, self._termino())
        return nodo

    def _termino(self):
        tok = self._ver()
        if tok is None or tok[0] in (")", "U"):
            raise ErrorExpresion(f"Falta un operando en la posición {self._pos_actual() + 1}.",
                                 self._pos_actual())
        nodo = self._factor()
        while (tok := self._ver()) is not None and tok[0] in self.INICIO_ATOMO:
            nodo = Concat(nodo, self._factor())
        return nodo

    def _factor(self):
        tok = self._ver()
        if tok[0] == "*":
            raise ErrorExpresion(f"La estrella '*' de la posición {tok[2] + 1} no tiene "
                                 "a qué aplicarse.", tok[2])
        nodo = self._atomo()
        while (tok := self._ver()) is not None and tok[0] == "*":
            self._avanzar()
            nodo = Estrella(nodo)
        return nodo

    def _atomo(self):
        tipo, valor, pos = self._avanzar()
        if tipo == "SIM":
            return Simbolo(valor)
        if tipo == "EPS":
            return Epsilon()
        if tipo == "VACIO":
            return Vacio()
        if tipo == "(":
            sig = self._ver()
            if sig is not None and sig[0] == ")":
                raise ErrorExpresion(f"Paréntesis vacíos en la posición {pos + 1}.", pos)
            nodo = self._expresion()
            sig = self._ver()
            if sig is None or sig[0] != ")":
                raise ErrorExpresion(f"Falta cerrar el paréntesis abierto en la posición {pos + 1}.", pos)
            self._avanzar()
            return nodo
        raise ErrorExpresion(f"Símbolo inesperado '{valor}' en la posición {pos + 1}.", pos)


def analizar(texto: str, alfabeto) -> object:
    """Convierte el texto de una expresión regular en su árbol sintáctico."""
    return Parser(_tokenizar(texto, alfabeto), texto).analizar()


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
_PRECEDENCIA = {Union: 1, Concat: 2, Estrella: 3}


def a_texto(nodo, padre: int = 0) -> str:
    """Escribe el árbol como texto, con los paréntesis mínimos necesarios."""
    if isinstance(nodo, Simbolo):
        return nodo.c
    if isinstance(nodo, Epsilon):
        return "ε"
    if isinstance(nodo, Vacio):
        return "∅"
    if isinstance(nodo, Caja):
        return nodo.nombre
    if isinstance(nodo, Estrella):
        texto, prec = a_texto(nodo.expr, 3) + "*", 3
    elif isinstance(nodo, Concat):
        texto, prec = a_texto(nodo.izq, 2) + a_texto(nodo.der, 2), 2
    elif isinstance(nodo, Union):
        texto, prec = a_texto(nodo.izq, 1) + " U " + a_texto(nodo.der, 1), 1
    else:
        raise TypeError(nodo)
    return f"({texto})" if prec < padre else texto


def a_regex_python(nodo) -> str:
    """Traduce a la sintaxis del módulo `re` de Python (se usa en las pruebas)."""
    import re
    if isinstance(nodo, Simbolo):
        return re.escape(nodo.c)
    if isinstance(nodo, Epsilon):
        return ""
    if isinstance(nodo, Vacio):
        return "(?!)"
    if isinstance(nodo, Union):
        return f"(?:{a_regex_python(nodo.izq)}|{a_regex_python(nodo.der)})"
    if isinstance(nodo, Concat):
        return f"(?:{a_regex_python(nodo.izq)}{a_regex_python(nodo.der)})"
    if isinstance(nodo, Estrella):
        return f"(?:{a_regex_python(nodo.expr)})*"
    raise TypeError(nodo)
