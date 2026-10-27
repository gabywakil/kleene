"""Dibujo de autómatas.

Una sola geometría (círculos, flechas, curvas, etiquetas) que se pinta de dos formas:
    - DibujanteTk  -> en un Canvas de Tkinter   (versión de escritorio)
    - DibujanteSVG -> como texto SVG            (versión web)
"""
from __future__ import annotations

import math
from html import escape

RADIO = 19            # radio de cada estado, en píxeles
ESCALA = 84           # píxeles por unidad del diagrama
MARGEN = 46

# Colores (claros y de buen contraste)
COLOR_TINTA = "#2b2d42"
COLOR_ESTADO = "#ffffff"
COLOR_RESALTE = "#ffd166"
COLOR_FLECHA_RESALTE = "#e63946"
COLOR_CAJA = "#e8eefc"


# ----------------------------------------------------------------------------
# Geometría compartida
# ----------------------------------------------------------------------------
def _unitario(dx, dy):
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def _cuadratica(p0, c, p2, n=26):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, d = (1 - t) ** 2, 2 * t * (1 - t), t * t
        pts.append((a * p0[0] + b * c[0] + d * p2[0], a * p0[1] + b * c[1] + d * p2[1]))
    return pts


def _cubica(p0, c1, c2, p3, n=26):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        pts.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0],
                    a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1]))
    return pts


def _flecha(punta, direccion, largo=10, ancho=4.6):
    dx, dy = direccion
    bx, by = punta[0] - largo * dx, punta[1] - largo * dy
    px, py = -dy, dx
    return [punta, (bx + ancho * px, by + ancho * py), (bx - ancho * px, by - ancho * py)]


def calcular_geometria(diagrama, escala=ESCALA, margen=MARGEN):
    """Convierte un Diagrama (unidades) en coordenadas de pantalla.

    Devuelve un dict con:
        nodos   {estado: (x, y)}
        aristas lista de dicts: u, v, etiqueta, caja, puntos, flecha, etiqueta_pos
        inicial_flecha  [(x0, y0), (x1, y1)]   la flecha que entra al estado inicial
        ancho, alto
    """
    nodos = {e: (x * escala, y * escala) for e, (x, y) in diagrama.pos.items()}
    aristas = []
    for a in diagrama.aristas:
        (x0, y0), (x1, y1) = nodos[a.u], nodos[a.v]
        sgn = 1 if a.curva >= 0 else -1
        if a.u == a.v:                                         # bucle sobre el estado
            p0 = (x0 - RADIO * 0.62, y0 - RADIO * 0.78)
            p3 = (x0 + RADIO * 0.62, y0 - RADIO * 0.78)
            pts = _cubica(p0, (x0 - RADIO * 1.7, y0 - RADIO * 3.1),
                          (x0 + RADIO * 1.7, y0 - RADIO * 3.1), p3)
            pos_etiqueta = (x0, y0 - RADIO * 2.55 - 8)
            punta = pts[-1]
            direccion = _unitario(punta[0] - pts[-2][0], punta[1] - pts[-2][1])
        else:
            ux, uy = _unitario(x1 - x0, y1 - y0)
            nx, ny = uy, -ux                                    # a la izquierda del sentido
            if abs(a.curva) < 1e-9:
                ctrl = ((x0 + x1) / 2, (y0 + y1) / 2)
                ini = (x0 + RADIO * ux, y0 + RADIO * uy)
                fin = (x1 - RADIO * ux, y1 - RADIO * uy)
                pts = [ini, fin]
                medio = ((ini[0] + fin[0]) / 2, (ini[1] + fin[1]) / 2)
            else:
                alto = 2 * a.curva * escala
                ctrl = ((x0 + x1) / 2 + nx * alto, (y0 + y1) / 2 + ny * alto)
                d0 = _unitario(ctrl[0] - x0, ctrl[1] - y0)
                d1 = _unitario(ctrl[0] - x1, ctrl[1] - y1)
                ini = (x0 + RADIO * d0[0], y0 + RADIO * d0[1])
                fin = (x1 + RADIO * d1[0], y1 + RADIO * d1[1])
                pts = _cuadratica(ini, ctrl, fin)
                medio = pts[len(pts) // 2]
            punta = pts[-1]
            direccion = _unitario(punta[0] - pts[-2][0], punta[1] - pts[-2][1])
            if a.tipo == "caja":
                pos_etiqueta = medio
            else:
                pos_etiqueta = (medio[0] + sgn * nx * 13, medio[1] + sgn * ny * 13)
        aristas.append({"u": a.u, "v": a.v, "etiqueta": a.etiqueta, "caja": a.tipo == "caja",
                        "puntos": pts, "flecha": _flecha(punta, direccion),
                        "etiqueta_pos": pos_etiqueta})

    ini_x, ini_y = nodos[diagrama.inicial]
    flecha_inicial = [(ini_x - RADIO - 30, ini_y), (ini_x - RADIO, ini_y)]

    # Caja que contiene todo el dibujo
    xs, ys = [], []
    for x, y in nodos.values():
        xs += [x - RADIO, x + RADIO]
        ys += [y - RADIO, y + RADIO]
    xs.append(flecha_inicial[0][0])
    for a in aristas:
        for x, y in a["puntos"]:
            xs.append(x)
            ys.append(y)
        ex, ey = a["etiqueta_pos"]
        w = 4.5 * len(a["etiqueta"]) + 10
        xs += [ex - w, ex + w]
        ys += [ey - 11, ey + 11]
    min_x, min_y = min(xs) - margen, min(ys) - margen

    def mover(p):
        return (p[0] - min_x, p[1] - min_y)

    nodos = {e: mover(p) for e, p in nodos.items()}
    for a in aristas:
        a["puntos"] = [mover(p) for p in a["puntos"]]
        a["flecha"] = [mover(p) for p in a["flecha"]]
        a["etiqueta_pos"] = mover(a["etiqueta_pos"])
    flecha_inicial = [mover(p) for p in flecha_inicial]
    return {"nodos": nodos, "aristas": aristas, "inicial_flecha": flecha_inicial,
            "ancho": max(xs) + margen - min_x, "alto": max(ys) + margen - min_y}


# ----------------------------------------------------------------------------
# Pintor para Tkinter
# ----------------------------------------------------------------------------
class DibujanteTk:
    """Dibuja un Diagrama sobre un tkinter.Canvas."""

    def __init__(self, canvas):
        self.canvas = canvas

    def dibujar(self, diagrama, ox=0, oy=0, resaltar_estados=(), resaltar_aristas=(),
                limpiar=True, escala=ESCALA):
        """resaltar_aristas: conjunto de pares (u, v). Devuelve (ancho, alto)."""
        c = self.canvas
        if limpiar:
            c.delete("all")
        g = calcular_geometria(diagrama, escala)
        fuente = ("Segoe UI", 11)
        fuente_estado = ("Segoe UI", 11, "bold")

        for a in g["aristas"]:
            resaltada = (a["u"], a["v"]) in resaltar_aristas
            color = COLOR_FLECHA_RESALTE if resaltada else COLOR_TINTA
            pts = [(x + ox, y + oy) for x, y in a["puntos"]]
            c.create_line(*[v for p in pts for v in p], fill=color, width=3 if resaltada else 1.6)
            c.create_polygon(*[v for p in a["flecha"] for v in (p[0] + ox, p[1] + oy)],
                             fill=color, outline=color)
            ex, ey = a["etiqueta_pos"][0] + ox, a["etiqueta_pos"][1] + oy
            if a["caja"]:
                w = 8 + 6 * len(a["etiqueta"])
                c.create_rectangle(ex - w, ey - 15, ex + w, ey + 15, fill=COLOR_CAJA,
                                   outline=COLOR_TINTA, width=1.4)
            c.create_text(ex, ey, text=a["etiqueta"], fill=color, font=fuente)

        x0, y0 = g["inicial_flecha"][0][0] + ox, g["inicial_flecha"][0][1] + oy
        x1, y1 = g["inicial_flecha"][1][0] + ox, g["inicial_flecha"][1][1] + oy
        c.create_line(x0, y0, x1, y1, fill=COLOR_TINTA, width=1.8)
        c.create_polygon(*[v for p in _flecha((x1, y1), (1, 0)) for v in p],
                         fill=COLOR_TINTA, outline=COLOR_TINTA)

        for e, (x, y) in g["nodos"].items():
            x, y = x + ox, y + oy
            relleno = COLOR_RESALTE if e in resaltar_estados else COLOR_ESTADO
            c.create_oval(x - RADIO, y - RADIO, x + RADIO, y + RADIO, fill=relleno,
                          outline=COLOR_TINTA, width=1.8)
            if e in diagrama.finales:
                c.create_oval(x - RADIO + 4, y - RADIO + 4, x + RADIO - 4, y + RADIO - 4,
                              outline=COLOR_TINTA, width=1.4)
            c.create_text(x, y, text=diagrama.nombres.get(e, str(e)), fill=COLOR_TINTA,
                          font=fuente_estado)
        return g["ancho"], g["alto"]


# ----------------------------------------------------------------------------
# Pintor SVG
# ----------------------------------------------------------------------------
class DibujanteSVG:
    """Dibuja un Diagrama como texto SVG (los colores se definen con clases CSS)."""

    @staticmethod
    def a_svg(diagrama, resaltar_estados=(), resaltar_aristas=(), escala=ESCALA) -> str:
        g = calcular_geometria(diagrama, escala)
        w, h = g["ancho"], g["alto"]
        partes = [f'<svg class="dibujo" xmlns="http://www.w3.org/2000/svg" '
                  f'viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" '
                  f'role="img">']
        for a in g["aristas"]:
            clase = "arista hl" if (a["u"], a["v"]) in resaltar_aristas else "arista"
            ruta = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in a["puntos"])
            flecha = " ".join(f"{x:.1f},{y:.1f}" for x, y in a["flecha"])
            ex, ey = a["etiqueta_pos"]
            partes.append(f'<g class="{clase}"><path d="{ruta}" fill="none"/>'
                          f'<polygon points="{flecha}"/>')
            if a["caja"]:
                ancho = 16 + 12 * len(a["etiqueta"])
                partes.append(f'<rect class="caja" x="{ex - ancho / 2:.1f}" y="{ey - 15:.1f}" '
                              f'width="{ancho}" height="30" rx="3"/>')
            partes.append(f'<text x="{ex:.1f}" y="{ey:.1f}" text-anchor="middle" '
                          f'dominant-baseline="central">{escape(a["etiqueta"])}</text></g>')
        (x0, y0), (x1, y1) = g["inicial_flecha"]
        punta = " ".join(f"{x:.1f},{y:.1f}" for x, y in _flecha((x1, y1), (1, 0)))
        partes.append(f'<g class="arista"><path d="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}" '
                      f'fill="none"/><polygon points="{punta}"/></g>')
        for e, (x, y) in g["nodos"].items():
            clase = "estado hl" if e in resaltar_estados else "estado"
            partes.append(f'<g class="{clase}"><circle cx="{x:.1f}" cy="{y:.1f}" r="{RADIO}"/>')
            if e in diagrama.finales:
                partes.append(f'<circle class="doble" cx="{x:.1f}" cy="{y:.1f}" r="{RADIO - 4}"/>')
            nombre = escape(str(diagrama.nombres.get(e, e)))
            partes.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
                          f'dominant-baseline="central">{nombre}</text></g>')
        partes.append("</svg>")
        return "".join(partes)
