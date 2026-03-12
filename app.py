import os
import sqlite3
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, abort
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
CORS(app)

# 1. CONFIGURACIÓN INICIAL
DB_NAME = "database.db"

# Datos del Blog
posts = [
    {
        "id": 1,
        "title": "Simulador de importación",
        "slug": "simulador-importacion",
        "excerpt": "Descubre cómo calcular costos logísticos.",
        "content": "Contenido completo del artículo...",
        "image": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d"
    }
]

# 2. FUNCIONES DE APOYO
def crear_tablas():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT,
        fecha TEXT,
        costo_total REAL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aranceles_cache (
        partida TEXT PRIMARY KEY,
        gravamen REAL,
        iva REAL,
        ultima_actualizacion TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # En Render, el binario ya está en el PATH, no se necesita Service o Manager
    return webdriver.Chrome(options=chrome_options)

def obtener_desde_cache(partida):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT gravamen, iva, ultima_actualizacion FROM aranceles_cache WHERE partida = ?", (partida,))
    resultado = cursor.fetchone()
    conn.close()
    if not resultado: return None
    gravamen, iva, fecha_str = resultado
    try:
        fecha_cache = datetime.fromisoformat(fecha_str)
        if datetime.now() - fecha_cache > timedelta(days=30): return None
    except: return None
    return {"gravamen": gravamen, "iva": iva, "desde_cache": True, "success": True}

def guardar_en_cache(partida, gravamen, iva):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO aranceles_cache (partida, gravamen, iva, ultima_actualizacion) VALUES (?, ?, ?, ?)",
                   (partida, gravamen, iva, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def scrapper_dian(subpartida):
    driver = None
    try:
        driver = get_driver()
        driver.get("https://muisca.dian.gov.co/WebArancel/DefConsultaGeneralNomenclaturas.faces")
        wait = WebDriverWait(driver, 30)
        
        wait.until(EC.presence_of_element_located((By.ID, "vistaConsultaGeneral:codigoNomenclatura")))
        driver.execute_script(f"document.getElementById('vistaConsultaGeneral:codigoNomenclatura').value = '{subpartida}';")
        
        btn_buscar = wait.until(EC.element_to_be_clickable((By.ID, "vistaConsultaGeneral:buscar")))
        driver.execute_script("arguments[0].click();", btn_buscar)
        
        btn_gravamen = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@id, 'linkGravamen')]")))
        driver.execute_script("arguments[0].click();", btn_gravamen)
        
        wait.until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[1])
        
        elemento_valor = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itxt")))
        valor_texto = elemento_valor.text.replace('%', '').replace(',', '.').strip()
        
        return {"gravamen": float(valor_texto), "iva": 19.0, "success": True, "desde_cache": False}
    except Exception as e:
        return {"error": "No se pudo consultar la DIAN.", "success": False}
    finally:
        if driver: driver.quit()

# 3. RUTAS DE NAVEGACIÓN
@app.route("/")
def home(): return render_template("index.html")

@app.route('/servicios')
def servicios(): return render_template('servicios.html')

@app.route('/blog')
def blog(): return render_template("blog.html", posts=posts)

@app.route('/blog/<slug>')
def post_detail(slug):
    post = next((p for p in posts if p["slug"] == slug), None)
    if not post: abort(404)
    return render_template("post.html", post=post)

@app.route('/contacto')
def contacto(): return render_template("contacto.html")

@app.route('/simulador')
def simulador(): return render_template("simulador.html")

@app.route('/login')
def login(): return render_template("login.html")

# 4. RUTAS DE API
@app.route('/consultar-arancel', methods=['GET'])
def consultar_arancel():
    partida = request.args.get('partida', '').strip()
    if not partida or not partida.isdigit():
        return jsonify({"error": "Partida inválida", "success": False}), 400
    
    resultado_cache = obtener_desde_cache(partida)
    if resultado_cache: return jsonify(resultado_cache)
    
    resultado = scrapper_dian(partida)
    if resultado.get('success'):
        guardar_en_cache(partida, resultado['gravamen'], resultado['iva'])
    return jsonify(resultado)

@app.route('/simular', methods=['POST'])
def simular():
    try:
        datos = request.json
        empresa = str(datos.get('empresa', 'Anonimo'))[:100]
        valor = float(datos.get('valor', 0))
        flete = float(datos.get('flete', 0))
        gravamen_aplicado = float(datos.get('gravamen', 0)) / 100
        
        cif = valor + flete
        arancel = cif * gravamen_aplicado
        iva = (cif + arancel) * 0.19
        total = cif + arancel + iva

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO simulaciones (empresa, fecha, costo_total) VALUES (?, ?, ?)",
                       (empresa, datetime.now().strftime("%Y-%m-%d %H:%M"), total))
        conn.commit()
        conn.close()

        return jsonify({"costo_total": round(total, 2), "arancel_calculado": round(arancel, 2),
                        "iva_calculado": round(iva, 2), "cif": round(cif, 2), "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/historial', methods=['GET'])
def historial():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT empresa, fecha, costo_total FROM simulaciones ORDER BY id DESC LIMIT 10")
    resultados = cursor.fetchall()
    conn.close()
    return jsonify([{"empresa": r[0], "fecha": r[1], "costo_total": r[2]} for r in resultados])

@app.route('/limpiar-cache', methods=['POST'])
def limpiar_cache():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM aranceles_cache")
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Cache limpiado", "success": True})

# 5. INICIO DE LA APLICACIÓN
if __name__ == "__main__":
    crear_tablas()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)