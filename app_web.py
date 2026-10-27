"""Versión web del aplicativo del Teorema de Kleene (Flask).

Ejecuta:   python app_web.py        y abre   http://127.0.0.1:5000
"""
from flask import Flask, jsonify, render_template, request

from kleene.conversiones import procesar
from kleene.dibujo import DibujanteSVG
from kleene.expresion import ALFABETOS, ErrorExpresion
from kleene.thompson import figuras_basicas

app = Flask(__name__)


def _svg(diagrama, estados=(), aristas=()):
    return DibujanteSVG.a_svg(diagrama, set(estados), set(aristas))


def _figuras():
    return [{"titulo": f["titulo"], "descripcion": f["descripcion"], "svg": _svg(f["diagrama"])}
            for f in figuras_basicas()]


def _contexto_resultado(res):
    """Convierte el Resultado del núcleo en datos listos para la plantilla."""
    pasos_thompson = [{"titulo": f"Paso {p.numero}: {p.tipo} · {p.expresion}",
                       "descripcion": p.descripcion,
                       "svg": _svg(p.diagrama, p.nuevos)} for p in res.thompson.pasos]
    afd = res.afd.afd
    return {
        "texto": res.texto,
        "pasos_thompson": pasos_thompson,
        "afd_filas": res.afd.filas,
        "simbolos": res.afd.simbolos,
        "afd_svg": _svg(res.diagrama_de("afd")),
        "n_afn": len(res.thompson.automata.estados),
        "n_afd": len(afd.estados),
        "n_min": len(res.minimo.minimo.estados),
        "rondas": res.minimo.rondas,
        "min_estados": [{"nombre": res.minimo.minimo.nombre(e),
                         "grupo": res.minimo.minimo.detalles[e],
                         "final": e in res.minimo.minimo.finales}
                        for e in res.minimo.minimo.estados],
        "min_svg": _svg(res.diagrama_de("minimo")),
        "pasos_er": [{"titulo": p.titulo, "descripcion": p.descripcion, "svg": _svg(p.diagrama)}
                     for p in res.er.pasos],
        "er_texto": res.er.texto,
        "equivalente": res.equivalente,
    }


@app.route("/", methods=["GET", "POST"])
def inicio():
    datos = {"expresion": "", "alfabeto": "abc", "ocultar_trampa": True,
             "error": None, "res": None}
    if request.method == "POST":
        datos["expresion"] = request.form.get("expresion", "").strip()
        datos["alfabeto"] = request.form.get("alfabeto", "abc")
        datos["ocultar_trampa"] = request.form.get("ocultar_trampa") == "on"
        if datos["alfabeto"] not in ALFABETOS:
            datos["alfabeto"] = "abc"
        try:
            res = procesar(datos["expresion"], datos["alfabeto"], datos["ocultar_trampa"])
            datos["res"] = _contexto_resultado(res)
        except ErrorExpresion as error:
            datos["error"] = error.mensaje
    return render_template("index.html", figuras=_figuras(), alfabetos=ALFABETOS, **datos)


@app.route("/api/probar", methods=["POST"])
def probar():
    """Simula una cadena sobre el AFN-ε, el AFD o el AFD mínimo, paso a paso."""
    d = request.get_json(force=True)
    clave = d.get("alfabeto", "abc")
    cual = d.get("automata", "minimo")
    if clave not in ALFABETOS or cual not in ("afn", "afd", "minimo"):
        return jsonify({"error": "Datos no válidos."}), 400
    try:
        res = procesar(d.get("expresion", ""), clave, bool(d.get("ocultar_trampa", True)))
        aut = res.automata_para_dibujo(cual)
        diagrama = res.diagrama_de(cual)
        acepta, pasos = aut.simular(d.get("cadena", ""))
    except (ErrorExpresion, ValueError) as error:
        return jsonify({"error": getattr(error, "mensaje", str(error))}), 400
    salida = []
    for p in pasos:
        leido = "Estado inicial" if p["simbolo"] is None else f"Se lee «{p['simbolo']}»"
        salida.append({"titulo": leido,
                       "estados": "Estados activos: " + aut.nombres_de(p["estados"]),
                       "svg": _svg(diagrama, p["estados"], {(u, v) for u, _, v in p["aristas"]})})
    return jsonify({"acepta": acepta, "pasos": salida})


if __name__ == "__main__":
    app.run(debug=True)
