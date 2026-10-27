"""Disposición (posiciones) de los estados para poder dibujar un autómata.

Las coordenadas están en "unidades": el módulo de dibujo las multiplica por una
escala en píxeles. El eje y crece hacia abajo, como en la pantalla.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .automata import EPSILON


@dataclass
class Arista:
    u: object
    v: object
    etiqueta: str
    curva: float = 0.0       # altura del arco (en unidades), hacia la izquierda del sentido u→v
    tipo: str = "normal"     # "normal" o "caja" (subautómata genérico R₁, R₂)


@dataclass
class Diagrama:
    estados: list
    nombres: dict
    pos: dict                # {estado: (x, y)}
    aristas: list            # lista de Arista
    inicial: object
    finales: set = field(default_factory=set)


def diagrama_por_capas(estados, nombres, aristas, inicial, finales,
                       sep_x: float = 1.75, sep_y: float = 1.35,
                       orden_simbolos=None) -> Diagrama:
    """Ubica los estados por capas según su distancia (BFS) al estado inicial.

    aristas: lista de (u, etiqueta, v). Las aristas paralelas se agrupan en una
    sola con las etiquetas separadas por comas.
    """
    orden_simbolos = orden_simbolos or []
    rango = {s: i for i, s in enumerate([EPSILON] + list(orden_simbolos))}

    # 1. Agrupar etiquetas de aristas paralelas
    agrupadas: dict[tuple, list] = {}
    for u, s, v in aristas:
        agrupadas.setdefault((u, v), []).append(s)

    # 2. Capas por BFS
    vecinos: dict = {e: [] for e in estados}
    for (u, v) in agrupadas:
        if v not in vecinos[u]:
            vecinos[u].append(v)
    capa = {inicial: 0}
    descubrimiento = [inicial]
    cola = deque([inicial])
    while cola:
        u = cola.popleft()
        for v in vecinos[u]:
            if v not in capa:
                capa[v] = capa[u] + 1
                descubrimiento.append(v)
                cola.append(v)
    extra = max(capa.values(), default=0) + 1
    for e in estados:                      # estados inalcanzables: al final
        if e not in capa:
            capa[e] = extra
            descubrimiento.append(e)

    # 3. Posiciones
    por_capa: dict[int, list] = {}
    for e in descubrimiento:
        por_capa.setdefault(capa[e], []).append(e)
    pos = {}
    for c, lista in por_capa.items():
        n = len(lista)
        for i, e in enumerate(lista):
            pos[e] = (c * sep_x, (i - (n - 1) / 2) * sep_y)

    # 4. Curvatura de cada arista para que no se monten
    lista_aristas = []
    for (u, v), simbolos in agrupadas.items():
        simbolos = sorted(simbolos, key=lambda s: (rango.get(s, 99), s))
        etiqueta = ", ".join(simbolos)
        if u == v:
            curva = 0.0                                    # bucle: lo resuelve el dibujo
        elif (v, u) in agrupadas:
            curva = 0.32                                   # ida y vuelta: un arco a cada lado
        else:
            salto = capa[v] - capa[u]
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            if salto == 1:
                curva = 0.0
            elif salto == 0:
                curva = 0.35 + 0.15 * abs(y1 - y0) / sep_y
            else:                                          # hacia atrás o saltando capas
                curva = 0.35 + 0.22 * (abs(salto) - 1)
                # si va hacia atrás por la misma fila, el arco pasa por debajo
                if salto < 0 and abs(y1 - y0) < 1e-9:
                    curva = 0.45 + 0.22 * (abs(salto) - 1)
        lista_aristas.append(Arista(u, v, etiqueta, curva))

    return Diagrama(list(estados), dict(nombres), pos, lista_aristas, inicial, set(finales))


def diagrama_de_automata(automata) -> Diagrama:
    return diagrama_por_capas(automata.estados, automata.nombres, automata.aristas(),
                              automata.inicial, automata.finales,
                              orden_simbolos=automata.alfabeto)
