"""Teorema de Kleene, parte 1:  expresión regular  →  AFN-ε  (construcción de Thompson).

Cada subexpresión produce un fragmento con UN estado inicial y UN estado final.
Las figuras base son:

    símbolo a :  (i) --a--> (f)
    ε         :  (i) --ε--> (f)
    ∅         :  (i)        (f)          (sin transiciones)
    R₁ U R₂   :  nuevo inicial con ε a ambos; ambos finales con ε al nuevo final
    R₁ R₂     :  final de R₁ --ε--> inicial de R₂
    R₁*       :  nuevo inicial y final; ε para entrar, ε para repetir y ε para saltar

Además de construir el autómata, este módulo calcula la posición de cada estado
siguiendo la forma de las figuras (la concatenación crece a lo ancho, la unión
apila los dos caminos y la estrella dibuja los arcos de repetir y saltar).
"""
from __future__ import annotations

from dataclasses import dataclass

from .automata import EPSILON, Automata
from .disposicion import Arista, Diagrama
from .expresion import (Caja, Concat, Epsilon, Estrella, Simbolo, Union, Vacio,
                        a_texto)

SEPARACION_UNION = 0.45     # espacio vertical entre los dos caminos de una unión
ALTURA_HOJA = 0.5
ALTURA_CAJA = 0.62
HOLGURA_ARCO = 0.38         # cuánto sobresale el arco de la estrella
ESPACIO_ETIQUETA = 0.3


@dataclass
class Fragmento:
    nodo: object
    inicio: int
    fin: int
    estados: list
    aristas: list            # lista de Arista (posiciones relativas a este fragmento)
    pos: dict
    ancho: float
    arriba: float            # cuánto ocupa por encima de la línea central
    abajo: float             # cuánto ocupa por debajo
    tipo: str = ""
    nuevos: tuple = ()       # estados creados en este paso (para resaltarlos)
    hijos: tuple = ()


@dataclass
class PasoThompson:
    numero: int
    tipo: str
    expresion: str
    descripcion: str
    diagrama: Diagrama
    nuevos: set              # estados agregados en este paso


@dataclass
class ResultadoThompson:
    automata: Automata
    diagrama: Diagrama
    pasos: list


def _desplazar(pos: dict, dx: float, dy: float) -> dict:
    return {e: (x + dx, y + dy) for e, (x, y) in pos.items()}


class ConstructorThompson:
    def __init__(self):
        self.contador = 0
        self.fragmentos: list[Fragmento] = []

    def _nuevo(self) -> int:
        self.contador += 1
        return self.contador - 1

    def construir(self, nodo) -> Fragmento:
        if isinstance(nodo, (Simbolo, Epsilon, Vacio, Caja)):
            frag = self.figura_hoja(nodo)
        elif isinstance(nodo, Concat):
            frag = self.figura_concatenacion(nodo)
        elif isinstance(nodo, Union):
            frag = self.figura_union(nodo)
        elif isinstance(nodo, Estrella):
            frag = self.figura_estrella(nodo)
        else:
            raise TypeError(nodo)
        self.fragmentos.append(frag)
        return frag

    # ------------------------------------------------------------------
    def figura_hoja(self, nodo) -> Fragmento:
        i, f = self._nuevo(), self._nuevo()
        ancho = 2.0 if isinstance(nodo, Caja) else 1.0
        alto = ALTURA_CAJA if isinstance(nodo, Caja) else ALTURA_HOJA
        aristas = []
        if isinstance(nodo, Simbolo):
            aristas.append(Arista(i, f, nodo.c))
            tipo = "símbolo"
        elif isinstance(nodo, Epsilon):
            aristas.append(Arista(i, f, EPSILON))
            tipo = "épsilon"
        elif isinstance(nodo, Caja):
            aristas.append(Arista(i, f, nodo.nombre, tipo="caja"))
            tipo = "subexpresión"
        else:
            tipo = "vacío"
        return Fragmento(nodo, i, f, [i, f], aristas, {i: (0.0, 0.0), f: (ancho, 0.0)},
                         ancho, alto, alto, tipo, (i, f))

    def figura_concatenacion(self, nodo) -> Fragmento:
        a = self.construir(nodo.izq)
        b = self.construir(nodo.der)
        dx = a.ancho + 1.0
        pos = dict(a.pos)
        pos.update(_desplazar(b.pos, dx, 0))
        aristas = list(a.aristas) + list(b.aristas) + [Arista(a.fin, b.inicio, EPSILON)]
        return Fragmento(nodo, a.inicio, b.fin, a.estados + b.estados, aristas, pos,
                         a.ancho + 1.0 + b.ancho, max(a.arriba, b.arriba),
                         max(a.abajo, b.abajo), "concatenación", (), (a, b))

    def figura_union(self, nodo) -> Fragmento:
        a = self.construir(nodo.izq)
        b = self.construir(nodo.der)
        i, f = self._nuevo(), self._nuevo()
        ancho_hijos = max(a.ancho, b.ancho)
        dy_a = -(a.abajo + SEPARACION_UNION)
        dy_b = b.arriba + SEPARACION_UNION
        pos = {i: (0.0, 0.0), f: (ancho_hijos + 2.0, 0.0)}
        pos.update(_desplazar(a.pos, 1.0 + (ancho_hijos - a.ancho) / 2, dy_a))
        pos.update(_desplazar(b.pos, 1.0 + (ancho_hijos - b.ancho) / 2, dy_b))
        aristas = list(a.aristas) + list(b.aristas) + [
            Arista(i, a.inicio, EPSILON), Arista(i, b.inicio, EPSILON),
            Arista(a.fin, f, EPSILON), Arista(b.fin, f, EPSILON)]
        return Fragmento(nodo, i, f, [i] + a.estados + b.estados + [f], aristas, pos,
                         ancho_hijos + 2.0, -dy_a + a.arriba, dy_b + b.abajo,
                         "unión", (i, f), (a, b))

    def figura_estrella(self, nodo) -> Fragmento:
        c = self.construir(nodo.expr)
        i, f = self._nuevo(), self._nuevo()
        pos = {i: (0.0, 0.0), f: (c.ancho + 2.0, 0.0)}
        pos.update(_desplazar(c.pos, 1.0, 0))
        alto_regreso = c.arriba + HOLGURA_ARCO
        alto_salto = c.abajo + HOLGURA_ARCO
        aristas = list(c.aristas) + [
            Arista(i, c.inicio, EPSILON),
            Arista(c.fin, f, EPSILON),
            # La curva es positiva hacia la izquierda del sentido de la arista.
            # El regreso va de derecha a izquierda: negativa = por encima.
            Arista(c.fin, c.inicio, EPSILON, curva=-alto_regreso),
            # El salto va de izquierda a derecha: negativa = por debajo.
            Arista(i, f, EPSILON, curva=-alto_salto),
        ]
        return Fragmento(nodo, i, f, [i] + c.estados + [f], aristas, pos, c.ancho + 2.0,
                         alto_regreso + ESPACIO_ETIQUETA, alto_salto + ESPACIO_ETIQUETA,
                         "estrella", (i, f), (c,))


# ----------------------------------------------------------------------------
def _renumerar(frag_final: Fragmento) -> dict:
    """Numera q0, q1, ... de izquierda a derecha y de arriba abajo."""
    orden = sorted(frag_final.estados,
                   key=lambda e: (round(frag_final.pos[e][0], 3), round(frag_final.pos[e][1], 3)))
    return {viejo: nuevo for nuevo, viejo in enumerate(orden)}


def _diagrama_de(frag: Fragmento, m: dict) -> Diagrama:
    estados = sorted(m[e] for e in frag.estados)
    return Diagrama(
        estados=estados,
        nombres={m[e]: f"q{m[e]}" for e in frag.estados},
        pos={m[e]: p for e, p in frag.pos.items()},
        aristas=[Arista(m[a.u], m[a.v], a.etiqueta, a.curva, a.tipo) for a in frag.aristas],
        inicial=m[frag.inicio],
        finales={m[frag.fin]},
    )


def _describir(frag: Fragmento, m: dict) -> str:
    q = lambda e: f"q{m[e]}"
    expr = a_texto(frag.nodo)
    if frag.tipo == "símbolo":
        return (f"Figura base del símbolo '{expr}': el estado inicial {q(frag.inicio)} "
                f"pasa al final {q(frag.fin)} leyendo '{expr}'.")
    if frag.tipo == "épsilon":
        return (f"Figura base de ε: {q(frag.inicio)} pasa a {q(frag.fin)} "
                "sin leer ningún símbolo.")
    if frag.tipo == "vacío":
        return (f"Figura base de ∅: {q(frag.inicio)} y {q(frag.fin)} no se conectan, "
                "así que no se acepta ninguna cadena.")
    if frag.tipo == "subexpresión":
        return f"Subautómata genérico N({expr})."
    if frag.tipo == "concatenación":
        a, b = frag.hijos
        return (f"Concatenación N({a_texto(a.nodo)})·N({a_texto(b.nodo)}): el final "
                f"{q(a.fin)} del primero se une con ε al inicial {q(b.inicio)} del segundo.")
    if frag.tipo == "unión":
        a, b = frag.hijos
        return (f"Unión N({a_texto(a.nodo)}) U N({a_texto(b.nodo)}): nuevo inicial "
                f"{q(frag.inicio)} con ε hacia {q(a.inicio)} y {q(b.inicio)}; los finales "
                f"{q(a.fin)} y {q(b.fin)} van con ε al nuevo final {q(frag.fin)}.")
    if frag.tipo == "estrella":
        (c,) = frag.hijos
        return (f"Estrella N({a_texto(c.nodo)})*: nuevo inicial {q(frag.inicio)} y nuevo "
                f"final {q(frag.fin)}. ε para entrar ({q(frag.inicio)}→{q(c.inicio)}), "
                f"ε para repetir ({q(c.fin)}→{q(c.inicio)}), ε para salir "
                f"({q(c.fin)}→{q(frag.fin)}) y ε para cero repeticiones "
                f"({q(frag.inicio)}→{q(frag.fin)}).")
    return ""


def thompson(arbol, alfabeto) -> ResultadoThompson:
    """Construye el AFN-ε de Thompson y la lista de pasos (una figura por subexpresión)."""
    constructor = ConstructorThompson()
    final = constructor.construir(arbol)
    m = _renumerar(final)

    pasos = []
    for n, frag in enumerate(constructor.fragmentos, start=1):
        pasos.append(PasoThompson(
            numero=n,
            tipo=frag.tipo,
            expresion=a_texto(frag.nodo),
            descripcion=_describir(frag, m),
            diagrama=_diagrama_de(frag, m),
            nuevos={m[e] for e in frag.nuevos},
        ))

    diagrama = _diagrama_de(final, m)
    aristas = [(a.u, a.etiqueta, a.v) for a in diagrama.aristas]
    automata = Automata.desde_aristas(diagrama.estados, alfabeto, aristas,
                                      diagrama.inicial, diagrama.finales,
                                      nombres=dict(diagrama.nombres), tipo="AFN-ε")
    return ResultadoThompson(automata, diagrama, pasos)


# ----------------------------------------------------------------------------
def figuras_basicas() -> list[dict]:
    """Las seis figuras del teorema de Kleene con subexpresiones genéricas R₁ y R₂."""
    r1, r2 = Caja("R₁"), Caja("R₂")
    casos = [
        ("Símbolo a", Simbolo("a"),
         "Para cada símbolo del alfabeto: un estado inicial y uno final unidos por ese símbolo."),
        ("Palabra vacía ε", Epsilon(),
         "Acepta solo la cadena vacía: se pasa al final sin leer nada."),
        ("Lenguaje vacío ∅", Vacio(),
         "No hay camino del inicial al final: no acepta ninguna cadena."),
        ("Unión R₁ U R₂", Union(r1, r2),
         "Un nuevo inicial se ramifica con ε hacia R₁ y R₂; ambos terminan con ε en un nuevo final."),
        ("Concatenación R₁R₂", Concat(r1, r2),
         "El final de R₁ se une con ε al inicial de R₂."),
        ("Estrella R₁*", Estrella(r1),
         "Nuevo inicial y final: ε para entrar, ε para repetir R₁ y ε para saltarlo (cero veces)."),
    ]
    figuras = []
    for titulo, nodo, descripcion in casos:
        constructor = ConstructorThompson()
        frag = constructor.construir(nodo)
        m = _renumerar(frag)
        figuras.append({"titulo": titulo, "descripcion": descripcion,
                        "diagrama": _diagrama_de(frag, m)})
    return figuras
