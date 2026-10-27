"""Teorema de Kleene, el resto del camino:

    ER ──Thompson──► AFN-ε ──subconjuntos──► AFD ──Moore──► AFD mínimo ──eliminación──► ER

Clases:
    ConvertidorAFD      AFN-ε → AFD (construcción de subconjuntos, con su tabla)
    Minimizador         AFD → AFD mínimo (refinamiento de particiones)
    EliminadorEstados   autómata → expresión regular (eliminación de estados)
La función `procesar` ejecuta todo el recorrido de una sola vez.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .automata import EPSILON, Automata
from .disposicion import Diagrama, diagrama_de_automata, diagrama_por_capas
from .expresion import (ALFABETOS, Concat, Epsilon, Estrella, Simbolo, Union, Vacio,
                        a_texto, analizar)
from .thompson import ResultadoThompson, thompson


def _nombre_letra(n: int) -> str:
    """0 -> A, 1 -> B, ... 25 -> Z, 26 -> A1, ..."""
    letra = chr(ord("A") + n % 26)
    return letra if n < 26 else f"{letra}{n // 26}"


# ============================================================================
# 1. AFN-ε  →  AFD   (construcción de subconjuntos)
# ============================================================================
@dataclass
class ResultadoAFD:
    afd: Automata
    filas: list          # una fila por estado del AFD (para mostrar la tabla)
    simbolos: list


class ConvertidorAFD:
    def __init__(self, afn: Automata):
        self.afn = afn

    def convertir(self) -> ResultadoAFD:
        afn = self.afn
        simbolos = list(afn.alfabeto)
        inicio = frozenset(afn.cierre_epsilon({afn.inicial}))
        ids = {inicio: 0}
        cola = deque([inicio])
        filas_crudas = []              # (conjunto, {simbolo: (mover, cierre)})
        while cola:
            conjunto = cola.popleft()
            fila = {}
            for s in simbolos:
                movido = afn.mover(conjunto, s)
                cierre = frozenset(afn.cierre_epsilon(movido))
                fila[s] = (movido, cierre)
                if cierre not in ids:
                    ids[cierre] = len(ids)
                    cola.append(cierre)
            filas_crudas.append((conjunto, fila))

        nombres = {i: _nombre_letra(i) for i in ids.values()}
        detalles, transiciones, finales, filas = {}, {}, set(), []
        for conjunto, fila in filas_crudas:
            origen = ids[conjunto]
            es_trampa = len(conjunto) == 0
            detalles[origen] = "∅ (estado trampa)" if es_trampa else afn.nombres_de(conjunto)
            es_final = bool(conjunto & afn.finales)
            if es_final:
                finales.add(origen)
            fila_tabla = {"estado": nombres[origen], "conjunto": afn.nombres_de(conjunto),
                          "inicial": origen == 0, "final": es_final, "trampa": es_trampa,
                          "transiciones": {}}
            for s, (movido, cierre) in fila.items():
                destino = ids[cierre]
                transiciones[(origen, s)] = {destino}
                fila_tabla["transiciones"][s] = {"mover": afn.nombres_de(movido),
                                                 "cierre": afn.nombres_de(cierre),
                                                 "destino": nombres[destino]}
            filas.append(fila_tabla)
        afd = Automata(list(ids.values()), simbolos, transiciones, 0, finales,
                       nombres=nombres, detalles=detalles, tipo="AFD")
        return ResultadoAFD(afd, filas, simbolos)


# ============================================================================
# 2. AFD  →  AFD mínimo   (refinamiento de particiones, algoritmo de Moore)
# ============================================================================
@dataclass
class ResultadoMinimo:
    minimo: Automata
    rondas: list         # lista de textos, uno por ronda de refinamiento
    grupos: list         # grupos finales (listas de nombres del AFD original)


class Minimizador:
    def __init__(self, afd: Automata):
        self.afd = afd

    def minimizar(self) -> ResultadoMinimo:
        afd = self.afd
        simbolos = afd.alfabeto
        destino = lambda e, s: next(iter(afd.destinos(e, s)))

        grupo = {e: (1 if e in afd.finales else 0) for e in afd.estados}
        rondas = []
        while True:
            tipos = sorted(set(grupo.values()))
            texto = " | ".join(
                afd.nombres_de([e for e in afd.estados if grupo[e] == g]) for g in tipos)
            rondas.append(f"Ronda {len(rondas)}:  {texto}")
            firma = {e: (grupo[e], tuple(grupo[destino(e, s)] for s in simbolos))
                     for e in afd.estados}
            nuevos_ids = {}
            nuevo = {}
            for e in afd.estados:
                nuevo[e] = nuevos_ids.setdefault(firma[e], len(nuevos_ids))
            if len(nuevos_ids) == len(set(grupo.values())):
                break
            grupo = nuevo

        # Numerar los grupos en el orden en que se descubren desde el inicial
        orden, vistos, cola = [], {}, deque([afd.inicial])
        vistos[grupo[afd.inicial]] = 0
        orden.append(grupo[afd.inicial])
        representante = {}
        for e in afd.estados:
            representante.setdefault(grupo[e], e)
        while cola:
            e = cola.popleft()
            for s in simbolos:
                g = grupo[destino(e, s)]
                if g not in vistos:
                    vistos[g] = len(vistos)
                    orden.append(g)
                    cola.append(representante[g])
        miembros = {g: [e for e in afd.estados if grupo[e] == g] for g in orden}
        nombres = {vistos[g]: f"M{vistos[g]}" for g in orden}
        detalles = {vistos[g]: afd.nombres_de(miembros[g]) for g in orden}
        trans = {(vistos[g], s): {vistos[grupo[destino(representante[g], s)]]}
                 for g in orden for s in simbolos}
        finales = {vistos[g] for g in orden if representante[g] in afd.finales}
        minimo = Automata([vistos[g] for g in orden], simbolos, trans, 0, finales,
                          nombres=nombres, detalles=detalles, tipo="AFD mínimo")
        rondas.append("Ya no se separan más grupos: cada grupo final es un estado del AFD mínimo.")
        return ResultadoMinimo(minimo, rondas, [detalles[vistos[g]] for g in orden])


def estados_utiles(automata: Automata) -> set:
    """Estados desde los que se puede llegar a un estado final."""
    inversas: dict = {}
    for u, _, v in automata.aristas():
        inversas.setdefault(v, set()).add(u)
    utiles = set(automata.finales)
    pila = list(utiles)
    while pila:
        v = pila.pop()
        for u in inversas.get(v, ()):
            if u not in utiles:
                utiles.add(u)
                pila.append(u)
    return utiles


def quitar_trampa(automata: Automata) -> Automata:
    """Copia del autómata sin los estados desde los que ya no se puede aceptar nada."""
    utiles = estados_utiles(automata) | {automata.inicial}
    estados = [e for e in automata.estados if e in utiles]
    trans = {(u, s): {v for v in vs if v in utiles}
             for (u, s), vs in automata.transiciones.items() if u in utiles}
    return Automata(estados, automata.alfabeto, trans, automata.inicial,
                    automata.finales & utiles, nombres=automata.nombres,
                    detalles=automata.detalles, tipo=automata.tipo)


def equivalentes(a: Automata, b: Automata) -> bool:
    """¿Aceptan el mismo lenguaje? Recorre los pares de estados de dos AFD completos."""
    visto = {(a.inicial, b.inicial)}
    cola = deque(visto)
    while cola:
        x, y = cola.popleft()
        if (x in a.finales) != (y in b.finales):
            return False
        for s in a.alfabeto:
            par = (next(iter(a.destinos(x, s))), next(iter(b.destinos(y, s))))
            if par not in visto:
                visto.add(par)
                cola.append(par)
    return True


# ============================================================================
# 3. Autómata  →  ER   (eliminación de estados)
# ============================================================================
def _suma(a, b):
    if isinstance(a, Vacio):
        return b
    if isinstance(b, Vacio) or a == b:
        return a
    return Union(a, b)


def _producto(a, b):
    if isinstance(a, Vacio) or isinstance(b, Vacio):
        return Vacio()
    if isinstance(a, Epsilon):
        return b
    if isinstance(b, Epsilon):
        return a
    return Concat(a, b)


def _estrella(a):
    if isinstance(a, (Vacio, Epsilon)):
        return Epsilon()
    return a if isinstance(a, Estrella) else Estrella(a)


@dataclass
class PasoER:
    titulo: str
    descripcion: str
    diagrama: Diagrama


@dataclass
class ResultadoER:
    expresion: object
    texto: str
    pasos: list


class EliminadorEstados:
    """Convierte un autómata en una expresión regular quitando un estado a la vez.

    Se agregan un estado inicial nuevo (INI) y uno final nuevo (FIN). Cada flecha
    queda etiquetada con una expresión regular. Al quitar el estado q, para cada
    camino  i → q → j  la flecha i → j pasa a ser:  R(i,j) U R(i,q) R(q,q)* R(q,j)
    """

    def __init__(self, automata: Automata):
        self.automata = automata

    def eliminar(self) -> ResultadoER:
        aut = self.automata
        R: dict = {}
        sumar = lambda u, v, r: R.__setitem__((u, v), _suma(R.get((u, v), Vacio()), r))
        sumar("INI", aut.inicial, Epsilon())
        for f in aut.finales:
            sumar(f, "FIN", Epsilon())
        for u, s, v in aut.aristas():
            sumar(u, v, Epsilon() if s == EPSILON else Simbolo(s))

        nombres = {e: aut.nombre(e) for e in aut.estados}
        nombres.update({"INI": "INI", "FIN": "FIN"})
        restantes = list(aut.estados)
        pasos = [PasoER("Autómata ampliado",
                        "Se agrega un estado inicial nuevo INI (con ε hacia el inicial) y un "
                        "estado final nuevo FIN (con ε desde cada final). Luego se eliminan los "
                        "estados originales de uno en uno; las flechas pasan a llevar "
                        "expresiones regulares.", self._diagrama(R, nombres, restantes))]

        while restantes:
            def costo(q):
                entran = sum(1 for (i, j), r in R.items() if j == q and i != q and not isinstance(r, Vacio))
                salen = sum(1 for (i, j), r in R.items() if i == q and j != q and not isinstance(r, Vacio))
                return entran * salen
            q = min(restantes, key=costo)
            restantes.remove(q)
            bucle = _estrella(R.get((q, q), Vacio()))
            entradas = [(i, r) for (i, j), r in R.items() if j == q and i != q and not isinstance(r, Vacio)]
            salidas = [(j, r) for (i, j), r in R.items() if i == q and j != q and not isinstance(r, Vacio)]
            for i, r_in in entradas:
                for j, r_out in salidas:
                    sumar(i, j, _producto(_producto(r_in, bucle), r_out))
            for clave in [k for k in R if q in k]:
                del R[clave]
            partes = []
            if not isinstance(bucle, Epsilon):
                partes.append(f"El bucle de {nombres[q]} queda como {a_texto(bucle)}")
            partes.append(f"cada camino que pasaba por {nombres[q]} se reemplaza por una flecha "
                          "directa con la expresión R(i,q) R(q,q)* R(q,j)")
            pasos.append(PasoER(f"Se elimina {nombres[q]}", "; ".join(partes) + ".",
                                self._diagrama(R, nombres, restantes)))

        final = R.get(("INI", "FIN"), Vacio())
        pasos[-1].descripcion += f" Solo quedan INI y FIN: la expresión regular es {a_texto(final)}."
        return ResultadoER(final, a_texto(final), pasos)

    @staticmethod
    def _diagrama(R, nombres, restantes) -> Diagrama:
        estados = ["INI"] + list(restantes) + ["FIN"]
        aristas = [(i, a_texto(r), j) for (i, j), r in R.items() if not isinstance(r, Vacio)]
        return diagrama_por_capas(estados, nombres, aristas, "INI", {"FIN"}, sep_x=2.5)


# ============================================================================
# Todo el recorrido
# ============================================================================
@dataclass
class Resultado:
    texto: str
    alfabeto: tuple
    arbol: object
    thompson: ResultadoThompson
    afd: ResultadoAFD
    minimo: ResultadoMinimo
    er: ResultadoER
    equivalente: bool
    ocultar_trampa: bool

    def automata_para_dibujo(self, cual: str) -> Automata:
        """'afn', 'afd' o 'minimo' (sin estado trampa si el usuario lo pidió)."""
        aut = {"afn": self.thompson.automata, "afd": self.afd.afd,
               "minimo": self.minimo.minimo}[cual]
        return quitar_trampa(aut) if self.ocultar_trampa and cual != "afn" else aut

    def diagrama_de(self, cual: str) -> Diagrama:
        return diagrama_de_automata(self.automata_para_dibujo(cual))


def procesar(texto: str, clave_alfabeto: str = "abc", ocultar_trampa: bool = True) -> Resultado:
    """Ejecuta el teorema de Kleene completo. Lanza ErrorExpresion si el texto es inválido."""
    alfabeto = ALFABETOS[clave_alfabeto]
    arbol = analizar(texto, alfabeto)
    t = thompson(arbol, alfabeto)
    afd = ConvertidorAFD(t.automata).convertir()
    minimo = Minimizador(afd.afd).minimizar()
    er = EliminadorEstados(quitar_trampa(minimo.minimo)).eliminar()

    # Comprobación: la ER obtenida debe describir el mismo lenguaje que la original
    afd_vuelta = Minimizador(ConvertidorAFD(thompson(er.expresion, alfabeto).automata)
                             .convertir().afd).minimizar().minimo
    return Resultado(texto, alfabeto, arbol, t, afd, minimo, er,
                     equivalentes(minimo.minimo, afd_vuelta), ocultar_trampa)
