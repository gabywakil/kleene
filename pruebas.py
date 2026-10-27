"""Pruebas automáticas del núcleo: todo el recorrido del teorema de Kleene.

Para muchas expresiones regulares al azar se comprueba que el AFN-ε, el AFD, el AFD
mínimo y el autómata de la expresión obtenida de vuelta aceptan EXACTAMENTE lo mismo
que el módulo `re` de Python.

Ejecuta:  python pruebas.py
"""
import itertools
import random
import re

from kleene.conversiones import procesar
from kleene.expresion import (ALFABETOS, Concat, Epsilon, Estrella, Simbolo, Union, Vacio,
                              a_regex_python, a_texto, analizar)
from kleene.thompson import thompson

random.seed(7)


def expresion_al_azar(alfabeto, profundidad):
    if profundidad == 0 or random.random() < 0.25:
        return random.choice([Simbolo(random.choice(alfabeto))] * 6 + [Epsilon(), Vacio()])
    tipo = random.choice(["union", "concat", "concat", "estrella"])
    if tipo == "estrella":
        return Estrella(expresion_al_azar(alfabeto, profundidad - 1))
    izq = expresion_al_azar(alfabeto, profundidad - 1)
    der = expresion_al_azar(alfabeto, profundidad - 1)
    return Union(izq, der) if tipo == "union" else Concat(izq, der)


def cadenas(alfabeto, largo_max):
    for n in range(largo_max + 1):
        for tupla in itertools.product(alfabeto, repeat=n):
            yield "".join(tupla)


total, fallos = 0, 0
for clave in ("abc", "01"):
    alfabeto = ALFABETOS[clave]
    pruebas = list(cadenas(alfabeto, 5 if clave == "abc" else 7))
    for _ in range(120):
        texto = a_texto(expresion_al_azar(alfabeto, 4))
        r = procesar(texto, clave)
        patron = re.compile(a_regex_python(analizar(texto, alfabeto)))
        vuelta = thompson(r.er.expresion, alfabeto).automata
        for cadena in pruebas:
            esperado = bool(patron.fullmatch(cadena))
            obtenidos = {
                "AFN-ε": r.thompson.automata.acepta(cadena),
                "AFD": r.afd.afd.acepta(cadena),
                "AFD mínimo": r.minimo.minimo.acepta(cadena),
                "ER de vuelta": vuelta.acepta(cadena),
            }
            for nombre, valor in obtenidos.items():
                total += 1
                if valor != esperado:
                    fallos += 1
                    print(f"FALLO {nombre}: ER={texto!r} cadena={cadena!r}")
        assert r.equivalente, f"La ER de vuelta no es equivalente: {texto!r}"
        assert len(r.minimo.minimo.estados) <= len(r.afd.afd.estados)

print(f"{total} comprobaciones, {fallos} fallos.")
print("TODO CORRECTO" if fallos == 0 else "HAY ERRORES")
