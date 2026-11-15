import os, re, json, hashlib
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder='.')
DB_FILE = "perfiles.json"

def cargar():
    data = json.load(open(DB_FILE, "r", encoding="utf-8")) if os.path.exists(DB_FILE) else {}
    data["maria-perez"] = {
        "nombre": "María Pérez (Demo)",
        "profesion": "Consultora Digital · Ejemplo VerixID",
        "documento_id": "Tax ID / NIT 900.000.000-1",
        "nostr_npub": "npub1verixiddemopublickey000000000000",
        "ubicacion": "🇨🇴 Colombia · Verificado",
        "canales": [
            {"red": "WhatsApp Principal", "usuario": "+57 300 000 0000", "url": "/registro"},
            {"red": "Correo Electrónico", "usuario": "maria@ejemplo.com", "url": "/registro"}
        ],
        "alerta_activa": "Perfil de demostración. Toca '+ Nuevo Escudo' arriba para crear el tuyo."
    }
    return data

def guardar(data):
    json.dump(data, open(DB_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def armar_url(tipo, valor):
    v, t = valor.strip(), tipo.lower()
    if v.startswith(("http://", "https://")): return v
    if "whatsapp" in t:
        num = "".join(c for c in v if c.isdigit())
        return "https://wa.me" + ("57" + num if len(num) == 10 and num.startswith("3") else num)
    if "telegram" in t: return "https://t.me" + v.lstrip("@")
    if "instagram" in t: return "https://instagram.com" + v.lstrip("@")
    if "correo" in t or ("@" in v and "." in v and not v.startswith("@")): return "mailto:" + v
    return "https://" + v.lstrip("@")

def verificar(perfil, consulta):
    q = consulta.lower().strip().lstrip("@").replace("https://", "").replace("www.", "").replace("mailto:", "")
    if not q: return None
    for c in perfil["canales"]:
        u = c["usuario"].lower().strip().lstrip("@")
        if q == u or (len(q) > 5 and q in c["url"].lower()):
            return {"tipo": "oficial", "titulo": "✅ CANAL 100% OFICIAL", "msg": f"Pertenece legítimamente a {perfil['nombre']} ({c['red']})."}
    for c in perfil["canales"]:
        u = c["usuario"].lower().strip().lstrip("@")
        if SequenceMatcher(None, q, u).ratio() >= 0.65 or (len(u) > 4 and u in q):
            return {"tipo": "clon", "titulo": "🚨 ALERTA: POSIBLE CLON", "msg": f"'{consulta}' imita '{c['usuario']}', pero NO está autorizado."}
    return {"tipo": "desconocido", "titulo": "⚠️ CANAL NO REGISTRADO", "msg": f"'{consulta}' no aparece en el escudo oficial de {perfil['nombre']}."}

@app.route("/")
def inicio():
    return render_template("splash.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        data = cargar()
        nombre = request.form.get("nombre", "").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-") or f"id-{int(datetime.now().timestamp())}"
        if slug in data: slug = f"{slug}-{int(datetime.now().timestamp()) % 1000}"
        t, v = request.form.get("canal_tipo", ""), request.form.get("canal_valor", "").strip()
        data[slug] = {
            "nombre": nombre,
            "profesion": request.form.get("profesion", "").strip(),
            "documento_id": request.form.get("documento_id", "").strip(),
            "nostr_npub": request.form.get("nostr_npub", "").strip(),
            "ubicacion": request.form.get("ubicacion", "🇨🇴 Colombia · Verificado"),
            "canales": [{"red": t, "usuario": v, "url": armar_url(t, v)}] if v else [],
            "alerta_activa": request.form.get("alerta_activa", "").strip()
        }
        guardar(data)
        return redirect(url_for("pasaporte", slug=slug))
    return render_template("registro.html")

@app.route("/v/<slug>", methods=["GET", "POST"])
def pasaporte(slug):
    data = cargar()
    p = data.get(slug)
    if not p: return "<script>localStorage.removeItem('verixid_mi_perfil');location.replace('/v/maria-perez?demo=1');</script>"
    cod = "VX-" + hashlib.sha256(slug.encode()).hexdigest()[:6].upper()
    res = verificar(p, request.form.get("canal", "")) if request.method == "POST" else None
    return render_template("pasaporte.html", slug=slug, perfil=p, codigo_id=cod, res=res, hora=datetime.now().strftime("%d/%m/%Y %H:%M"))

@app.route("/v/<slug>/agregar", methods=["POST"])
def agregar(slug):
    data = cargar()
    if slug in data and slug != "maria-perez":
        t, v = request.form.get("tipo", ""), request.form.get("valor", "").strip()
        if v:
            data[slug]["canales"].append({"red": t, "usuario": v, "url": armar_url(t, v)})
            guardar(data)
    return redirect(url_for("pasaporte", slug=slug))

@app.route("/v/<slug>/quitar/<int:idx>", methods=["POST"])
def quitar(slug, idx):
    data = cargar()
    if slug in data and slug != "maria-perez" and 0 <= idx < len(data[slug]["canales"]) and len(data[slug]["canales"]) > 1:
        data[slug]["canales"].pop(idx)
        guardar(data)
    return redirect(url_for("pasaporte", slug=slug))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
