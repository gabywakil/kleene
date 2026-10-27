"""Autómata finito genérico (sirve para AFN-ε, AFN y AFD)."""
from __future__ import annotations

EPSILON = "ε"


class Automata:
    def __init__(self, estados, alfabeto, transiciones, inicial, finales,
                 nombres=None, detalles=None, tipo="AFN-ε"):
        """
        transiciones: dict {(estado, simbolo): conjunto de estados destino}
                      el símbolo EPSILON representa una transición ε.
        nombres:      dict {estado: texto que se dibuja}            (opcional)
        detalles:     dict {estado: explicación, p. ej. el subconjunto} (opcional)
        """
        self.estados = list(estados)
        self.alfabeto = list(alfabeto)
        self.transiciones = {k: set(v) for k, v in transiciones.items() if v}
        self.inicial = inicial
        self.finales = set(finales)
        self.nombres = nombres or {e: f"q{e}" for e in self.estados}
        self.detalles = detalles or {}
        self.tipo = tipo

    # ------------------------------------------------------------------
    @classmethod
    def desde_aristas(cls, estados, alfabeto, aristas, inicial, finales, **kw):
        """Crea el autómata a partir de una lista de aristas (origen, simbolo, destino)."""
        trans = {}
        for u, s, v in aristas:
            trans.setdefault((u, s), set()).add(v)
        return cls(estados, alfabeto, trans, inicial, finales, **kw)

    def nombre(self, e) -> str:
        return self.nombres.get(e, str(e))

    def nombres_de(self, conjunto) -> str:
        if not conjunto:
            return "∅"
        orden = {e: i for i, e in enumerate(self.estados)}
        return "{" + ", ".join(self.nombre(e) for e in sorted(conjunto, key=orden.get)) + "}"

    def destinos(self, estado, simbolo) -> set:
        return self.transiciones.get((estado, simbolo), set())

    def aristas(self) -> list[tuple]:
        orden = {e: i for i, e in enumerate(self.estados)}
        orden_s = {s: i for i, s in enumerate([EPSILON] + self.alfabeto)}
        lista = [(u, s, v) for (u, s), dest in self.transiciones.items() for v in dest]
        return sorted(lista, key=lambda t: (orden[t[0]], orden_s.get(t[1], 99), orden[t[2]]))

    def es_determinista(self) -> bool:
        if any(s == EPSILON for (_, s) in self.transiciones):
            return False
        return all(len(d) == 1 for d in self.transiciones.values())

    # ------------------------------------------------------------------
    def cierre_epsilon(self, conjunto) -> set:
        """Todos los estados alcanzables desde `conjunto` usando solo transiciones ε."""
        resultado = set(conjunto)
        pila = list(conjunto)
        while pila:
            u = pila.pop()
            for v in self.destinos(u, EPSILON):
                if v not in resultado:
                    resultado.add(v)
                    pila.append(v)
        return resultado

    def mover(self, conjunto, simbolo) -> set:
        """Estados alcanzables desde `conjunto` leyendo exactamente `simbolo`."""
        resultado = set()
        for u in conjunto:
            resultado |= self.destinos(u, simbolo)
        return resultado

    def simular(self, cadena: str):
        """Recorre la cadena. Devuelve (acepta, pasos).

        Cada paso es un dict con:
            simbolo  -> símbolo leído (None en el paso inicial)
            estados  -> conjunto de estados activos tras leerlo (con cierre ε)
            aristas  -> aristas (u, simbolo, v) usadas al leerlo
        """
        for i, ch in enumerate(cadena):
            if ch not in self.alfabeto:
                raise ValueError(f"El símbolo '{ch}' (posición {i + 1}) no pertenece al "
                                 f"alfabeto {{{', '.join(self.alfabeto)}}}.")
        actual = self.cierre_epsilon({self.inicial})
        pasos = [{"simbolo": None, "estados": frozenset(actual), "aristas": set()}]
        for ch in cadena:
            usadas = {(u, ch, v) for u in actual for v in self.destinos(u, ch)}
            actual = self.cierre_epsilon(self.mover(actual, ch))
            pasos.append({"simbolo": ch, "estados": frozenset(actual), "aristas": usadas})
        return bool(actual & self.finales), pasos

    def acepta(self, cadena: str) -> bool:
        return self.simular(cadena)[0]
