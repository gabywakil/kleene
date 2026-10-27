"""Versión de escritorio del aplicativo del Teorema de Kleene (Tkinter).

Ejecuta:   python app_escritorio.py
"""
import tkinter as tk
from tkinter import ttk

from kleene.conversiones import procesar
from kleene.dibujo import DibujanteTk
from kleene.expresion import ALFABETOS, ErrorExpresion
from kleene.thompson import figuras_basicas

FUENTE = ("Segoe UI", 10)
FUENTE_TITULO = ("Segoe UI", 11, "bold")
FUENTE_CODIGO = ("Consolas", 12)
COLOR_OK = "#1b8a5a"
COLOR_ERROR = "#c1272d"


class LienzoDesplazable(ttk.Frame):
    """Un Canvas con barras de desplazamiento y un dibujante de autómatas."""

    def __init__(self, padre, alto=300):
        super().__init__(padre)
        self.canvas = tk.Canvas(self, background="white", highlightthickness=0, height=alto)
        barra_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        barra_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=barra_x.set, yscrollcommand=barra_y.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.dibujante = DibujanteTk(self.canvas)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>",
                         lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))

    def pintar(self, diagrama, resaltar_estados=(), resaltar_aristas=()):
        ancho, alto = self.dibujante.dibujar(diagrama, resaltar_estados=resaltar_estados,
                                             resaltar_aristas=resaltar_aristas)
        self.canvas.configure(scrollregion=(0, 0, ancho, alto))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def limpiar(self):
        self.canvas.delete("all")
        self.canvas.configure(scrollregion=(0, 0, 0, 0))


class VisorPasos(ttk.Frame):
    """Muestra una lista de pasos (título, explicación y dibujo) con botones Anterior/Siguiente."""

    def __init__(self, padre, alto=300):
        super().__init__(padre)
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 4))
        self.boton_ant = ttk.Button(barra, text="◀ Anterior", command=lambda: self.ir(-1))
        self.boton_sig = ttk.Button(barra, text="Siguiente ▶", command=lambda: self.ir(1))
        self.boton_ant.pack(side="left")
        self.boton_sig.pack(side="left", padx=6)
        self.var_cuenta = tk.StringVar()
        ttk.Label(barra, textvariable=self.var_cuenta, font=FUENTE).pack(side="right")
        self.var_titulo = tk.StringVar()
        self.var_descripcion = tk.StringVar()
        ttk.Label(self, textvariable=self.var_titulo, font=FUENTE_TITULO).pack(anchor="w")
        self.etiqueta = ttk.Label(self, textvariable=self.var_descripcion, font=FUENTE,
                                  wraplength=900, justify="left")
        self.etiqueta.pack(anchor="w", fill="x", pady=(0, 4))
        self.bind("<Configure>", lambda e: self.etiqueta.configure(wraplength=max(300, e.width - 20)))
        self.lienzo = LienzoDesplazable(self, alto)
        self.lienzo.pack(fill="both", expand=True)
        self.pasos, self.n = [], 0

    def cargar(self, pasos, inicio=0):
        """pasos: lista de dicts con titulo, descripcion, diagrama y (opcional) estados/aristas."""
        self.pasos = pasos
        self.n = inicio
        self._mostrar()

    def ir(self, delta):
        self.n = max(0, min(len(self.pasos) - 1, self.n + delta))
        self._mostrar()

    def _mostrar(self):
        if not self.pasos:
            self.var_titulo.set("")
            self.var_descripcion.set("")
            self.var_cuenta.set("")
            self.lienzo.limpiar()
            return
        p = self.pasos[self.n]
        self.var_titulo.set(p["titulo"])
        self.var_descripcion.set(p["descripcion"])
        self.var_cuenta.set(f"Paso {self.n + 1} de {len(self.pasos)}")
        self.boton_ant.state(["!disabled"] if self.n > 0 else ["disabled"])
        self.boton_sig.state(["!disabled"] if self.n < len(self.pasos) - 1 else ["disabled"])
        self.lienzo.pintar(p["diagrama"], p.get("estados", ()), p.get("aristas", ()))


class AppKleene(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Teorema de Kleene")
        self.geometry("1180x800")
        self.minsize(900, 620)
        self.res = None
        self._construir_entrada()
        self._construir_pestanas()
        self._dibujar_figuras()
        self.var_expr.set("(a U b)*abc")
        self.after(150, self.dibujar)

    # ------------------------------------------------------------------
    # Parte superior: expresión, alfabeto y botón
    # ------------------------------------------------------------------
    def _construir_entrada(self):
        marco = ttk.Frame(self, padding=(12, 10))
        marco.pack(fill="x")
        ttk.Label(marco, text="Expresión regular", font=FUENTE_TITULO).grid(row=0, column=0, sticky="w")
        self.var_expr = tk.StringVar()
        self.entrada = ttk.Entry(marco, textvariable=self.var_expr, font=("Consolas", 16))
        self.entrada.grid(row=1, column=0, columnspan=4, sticky="ew", pady=4)
        self.entrada.bind("<Return>", self.dibujar)
        marco.columnconfigure(3, weight=1)

        simbolos = ttk.Frame(marco)
        simbolos.grid(row=2, column=0, columnspan=4, sticky="w")
        for s in ["U", "*", "(", ")", "ε", "∅"]:
            ttk.Button(simbolos, text=s, width=3, command=lambda s=s: self._insertar(s)).pack(side="left", padx=2)

        opciones = ttk.Frame(marco)
        opciones.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Label(opciones, text="Alfabeto:", font=FUENTE).pack(side="left")
        self.var_alfabeto = tk.StringVar(value="abc")
        for clave, simbolos_alfabeto in ALFABETOS.items():
            ttk.Radiobutton(opciones, text="{ " + ", ".join(simbolos_alfabeto) + " }",
                            variable=self.var_alfabeto, value=clave,
                            command=self.dibujar).pack(side="left", padx=8)
        self.var_trampa = tk.BooleanVar(value=True)
        ttk.Checkbutton(opciones, text="Ocultar estado trampa (∅)", variable=self.var_trampa,
                        command=self.dibujar).pack(side="left", padx=14)
        ttk.Button(opciones, text="Dibujar", command=self.dibujar).pack(side="right")

        self.var_error = tk.StringVar()
        tk.Label(marco, textvariable=self.var_error, fg=COLOR_ERROR, font=FUENTE,
                 anchor="w").grid(row=4, column=0, columnspan=4, sticky="ew")

    def _insertar(self, simbolo):
        self.entrada.insert(tk.INSERT, simbolo)
        self.entrada.focus_set()

    # ------------------------------------------------------------------
    # Pestañas
    # ------------------------------------------------------------------
    def _construir_pestanas(self):
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Figuras base
        self.lienzo_figuras = LienzoDesplazable(self.pestanas)
        self.pestanas.add(self.lienzo_figuras, text="Figuras de Kleene")

        # 1. Thompson
        self.visor_thompson = VisorPasos(self.pestanas)
        self.pestanas.add(self.visor_thompson, text="1 · ER → AFN-ε")

        # 2. AFD
        panel = ttk.PanedWindow(self.pestanas, orient="vertical")
        marco_tabla = ttk.Frame(panel)
        self.tabla = ttk.Treeview(marco_tabla, show="headings", height=7)
        barra_t = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_t.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra_t.pack(side="right", fill="y")
        self.lienzo_afd = LienzoDesplazable(panel)
        panel.add(marco_tabla, weight=1)
        panel.add(self.lienzo_afd, weight=2)
        self.pestanas.add(panel, text="2 · AFN-ε → AFD")

        # 3. Mínimo
        panel_min = ttk.PanedWindow(self.pestanas, orient="vertical")
        self.texto_min = tk.Text(panel_min, height=9, wrap="word", font=("Consolas", 11),
                                 state="disabled", background="#f6f7fb", relief="flat")
        self.lienzo_min = LienzoDesplazable(panel_min)
        panel_min.add(self.texto_min, weight=1)
        panel_min.add(self.lienzo_min, weight=2)
        self.pestanas.add(panel_min, text="3 · AFD mínimo")

        # 4. Autómata → ER
        marco_er = ttk.Frame(self.pestanas)
        self.visor_er = VisorPasos(marco_er, alto=240)
        self.visor_er.pack(fill="both", expand=True)
        pie = ttk.Frame(marco_er, padding=(0, 8, 0, 0))
        pie.pack(fill="x")
        ttk.Label(pie, text="Resultado:", font=FUENTE_TITULO).pack(side="left")
        self.var_er = tk.StringVar()
        ttk.Entry(pie, textvariable=self.var_er, font=FUENTE_CODIGO, state="readonly").pack(
            side="left", fill="x", expand=True, padx=8)
        self.var_equivalente = tk.StringVar()
        self.etiqueta_equivalente = tk.Label(pie, textvariable=self.var_equivalente, font=FUENTE_TITULO)
        self.etiqueta_equivalente.pack(side="left")
        self.pestanas.add(marco_er, text="4 · Autómata → ER")

        # 5. Probar cadena
        marco_p = ttk.Frame(self.pestanas, padding=6)
        barra = ttk.Frame(marco_p)
        barra.pack(fill="x", pady=(0, 6))
        ttk.Label(barra, text="Cadena:", font=FUENTE_TITULO).pack(side="left")
        self.var_cadena = tk.StringVar()
        entrada_cadena = ttk.Entry(barra, textvariable=self.var_cadena, font=FUENTE_CODIGO, width=22)
        entrada_cadena.pack(side="left", padx=8)
        entrada_cadena.bind("<Return>", self.probar)
        self.var_automata = tk.StringVar(value="AFD mínimo")
        ttk.Combobox(barra, textvariable=self.var_automata, state="readonly", width=12,
                     values=["AFD mínimo", "AFD", "AFN-ε"]).pack(side="left")
        ttk.Button(barra, text="Probar", command=self.probar).pack(side="left", padx=8)
        self.var_veredicto = tk.StringVar()
        self.etiqueta_veredicto = tk.Label(barra, textvariable=self.var_veredicto, font=FUENTE_TITULO)
        self.etiqueta_veredicto.pack(side="left", padx=8)
        self.visor_prueba = VisorPasos(marco_p)
        self.visor_prueba.pack(fill="both", expand=True)
        self.pestanas.add(marco_p, text="5 · Probar cadena")

    # ------------------------------------------------------------------
    # Contenido
    # ------------------------------------------------------------------
    def _dibujar_figuras(self):
        """Dibuja las seis figuras base una debajo de otra en un mismo lienzo."""
        lienzo = self.lienzo_figuras
        c = lienzo.canvas
        y, ancho_total = 14, 0
        for f in figuras_basicas():
            c.create_text(16, y, text=f["titulo"], anchor="nw", font=FUENTE_TITULO, fill="#2b2d42")
            descripcion = c.create_text(16, y + 24, text=f["descripcion"], anchor="nw", font=FUENTE,
                                        fill="#6b6f86", width=760)
            y = c.bbox(descripcion)[3] + 4
            ancho, alto = lienzo.dibujante.dibujar(f["diagrama"], oy=y, limpiar=False)
            y += alto + 16
            ancho_total = max(ancho_total, ancho)
        c.configure(scrollregion=(0, 0, max(ancho_total, 800), y))

    def dibujar(self, _evento=None):
        texto = self.var_expr.get().strip()
        try:
            self.res = procesar(texto, self.var_alfabeto.get(), self.var_trampa.get())
        except ErrorExpresion as error:
            self.var_error.set("⚠ " + error.mensaje)
            if error.posicion is not None:
                self.entrada.icursor(error.posicion)
            self.entrada.focus_set()
            return
        self.var_error.set("")
        r = self.res

        self.visor_thompson.cargar([
            {"titulo": f"Paso {p.numero}: {p.tipo} · {p.expresion}", "descripcion": p.descripcion,
             "diagrama": p.diagrama, "estados": p.nuevos} for p in r.thompson.pasos],
            inicio=0)
        if self.pestanas.index("current") == 0:      # desde las figuras, pasa a la construcción
            self.pestanas.select(self.visor_thompson)

        self._llenar_tabla_afd(r)
        self.lienzo_afd.pintar(r.diagrama_de("afd"))

        self._llenar_texto_min(r)
        self.lienzo_min.pintar(r.diagrama_de("minimo"))

        self.visor_er.cargar([{"titulo": p.titulo, "descripcion": p.descripcion,
                               "diagrama": p.diagrama} for p in r.er.pasos])
        self.var_er.set(r.er.texto)
        self.var_equivalente.set("✔ Equivalente a la original" if r.equivalente else "✖ No equivalente")
        self.etiqueta_equivalente.configure(fg=COLOR_OK if r.equivalente else COLOR_ERROR)

        self.var_veredicto.set("")
        self.visor_prueba.cargar([])

    def _llenar_tabla_afd(self, r):
        columnas = ["estado", "conjunto"] + list(r.afd.simbolos)
        self.tabla.delete(*self.tabla.get_children())
        self.tabla["columns"] = columnas
        self.tabla.heading("estado", text="Estado")
        self.tabla.column("estado", width=70, anchor="w", stretch=False)
        self.tabla.heading("conjunto", text="Conjunto del AFN-ε")
        self.tabla.column("conjunto", width=260, anchor="w")
        for s in r.afd.simbolos:
            self.tabla.heading(s, text=f"Con «{s}»:  mover → cierre-ε → destino")
            self.tabla.column(s, width=330, anchor="w")
        for f in r.afd.filas:
            nombre = ("→ " if f["inicial"] else "") + f["estado"] + (" *" if f["final"] else "")
            celdas = [f"{t['mover']} → {t['cierre']} → {t['destino']}"
                      for t in (f["transiciones"][s] for s in r.afd.simbolos)]
            self.tabla.insert("", "end", values=[nombre, f["conjunto"]] + celdas)

    def _llenar_texto_min(self, r):
        lineas = ["Rondas de refinamiento:"] + ["  " + x for x in r.minimo.rondas]
        lineas += ["", "Estados del AFD mínimo:"]
        m = r.minimo.minimo
        for e in m.estados:
            lineas.append(f"  {m.nombre(e)}{' *' if e in m.finales else ''} = {m.detalles[e]}")
        lineas.append(f"\nEl AFD pasó de {len(r.afd.afd.estados)} a {len(m.estados)} estados.")
        self.texto_min.configure(state="normal")
        self.texto_min.delete("1.0", "end")
        self.texto_min.insert("end", "\n".join(lineas))
        self.texto_min.configure(state="disabled")

    def probar(self, _evento=None):
        if self.res is None:
            self._veredicto("Primero dibuja una expresión.", COLOR_ERROR)
            return
        cual = {"AFD mínimo": "minimo", "AFD": "afd", "AFN-ε": "afn"}[self.var_automata.get()]
        automata = self.res.automata_para_dibujo(cual)
        diagrama = self.res.diagrama_de(cual)
        try:
            acepta, pasos = automata.simular(self.var_cadena.get().strip())
        except ValueError as error:
            self._veredicto("⚠ " + str(error), COLOR_ERROR)
            self.visor_prueba.cargar([])
            return
        self.visor_prueba.cargar([
            {"titulo": "Estado inicial" if p["simbolo"] is None else f"Se lee «{p['simbolo']}»",
             "descripcion": "Estados activos: " + automata.nombres_de(p["estados"]),
             "diagrama": diagrama, "estados": p["estados"],
             "aristas": {(u, v) for u, _, v in p["aristas"]}} for p in pasos])
        self._veredicto("✔ Cadena ACEPTADA" if acepta else "✖ Cadena RECHAZADA",
                        COLOR_OK if acepta else COLOR_ERROR)

    def _veredicto(self, texto, color):
        self.var_veredicto.set(texto)
        self.etiqueta_veredicto.configure(fg=color)


if __name__ == "__main__":
    AppKleene().mainloop()
