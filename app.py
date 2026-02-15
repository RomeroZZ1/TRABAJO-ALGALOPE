from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
import time
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# ------------------------------
# CORS CONFIGURADO
# ------------------------------
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:5000", "http://localhost:5500"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

DB_NAME = "database.db"

# ------------------------------
# RUTA PRINCIPAL (SOLUCIONA 404)
# ------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route('/servicios')
def servicios():
    return render_template('servicios.html')

@app.route('/blog')
def blog():
    return render_template("blog.html", posts=posts)

@app.route('/contacto')
def contacto():
    return render_template("contacto.html")

@app.route('/simulador')
def simulador():
    return render_template("simulador.html")

@app.route('/login')
def login():
    return render_template("login.html")

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



@app.route('/blog/<slug>')
def post_detail(slug):
    post = next((p for p in posts if p["slug"] == slug), None)
    if not post:
        abort(404)
    return render_template("post.html", post=post)

# ------------------------------
# CREAR TABLAS
# ------------------------------
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

crear_tablas()

# ------------------------------
# OBTENER DESDE CACHE
# ------------------------------
def obtener_desde_cache(partida):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT gravamen, iva, ultima_actualizacion 
        FROM aranceles_cache 
        WHERE partida = ?
    """, (partida,))
    
    resultado = cursor.fetchone()
    conn.close()
    
    if not resultado:
        return None
    
    gravamen, iva, fecha_str = resultado
    
    try:
        fecha_cache = datetime.fromisoformat(fecha_str)
        if datetime.now() - fecha_cache > timedelta(days=30):
            return None
    except:
        return None
    
    return {"gravamen": gravamen, "iva": iva, "desde_cache": True, "success": True}

# ------------------------------
# GUARDAR EN CACHE
# ------------------------------
def guardar_en_cache(partida, gravamen, iva):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO aranceles_cache (partida, gravamen, iva, ultima_actualizacion)
        VALUES (?, ?, ?, ?)
    """, (partida, gravamen, iva, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

# ------------------------------
# SCRAPER DIAN
# ------------------------------
def scrapper_dian(subpartida):

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = None
    
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )
        
        driver.get("https://muisca.dian.gov.co/WebArancel/DefConsultaGeneralNomenclaturas.faces")
        wait = WebDriverWait(driver, 30)
        
        wait.until(EC.presence_of_element_located((By.ID, "vistaConsultaGeneral:codigoNomenclatura")))
        
        script = f"document.getElementById('vistaConsultaGeneral:codigoNomenclatura').value = '{subpartida}';"
        driver.execute_script(script)
        
        btn_buscar = wait.until(EC.element_to_be_clickable((By.ID, "vistaConsultaGeneral:buscar")))
        driver.execute_script("arguments[0].click();", btn_buscar)
        
        btn_gravamen = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@id, 'linkGravamen')]")))
        driver.execute_script("arguments[0].click();", btn_gravamen)
        
        wait.until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[1])
        
        elemento_valor = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itxt")))
        valor_texto = elemento_valor.text.replace('%', '').replace(',', '.').strip()
        
        gravamen = float(valor_texto)
        
        return {"gravamen": gravamen, "iva": 19.0, "success": True, "desde_cache": False}

    except Exception as e:
        return {
            "error": "No se pudo consultar la DIAN.",
            "success": False
        }
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

# ------------------------------
# CONSULTAR ARANCEL
# ------------------------------
@app.route('/consultar-arancel', methods=['GET'])
def consultar_arancel():
    partida = request.args.get('partida', '').strip()
    
    if not partida or not partida.isdigit():
        return jsonify({
            "error": "Partida inválida",
            "success": False
        }), 400
    
    resultado_cache = obtener_desde_cache(partida)
    if resultado_cache:
        return jsonify(resultado_cache)
    
    resultado = scrapper_dian(partida)
    
    if resultado.get('success'):
        guardar_en_cache(partida, resultado['gravamen'], resultado['iva'])
    
    return jsonify(resultado)

# ------------------------------
# SIMULAR
# ------------------------------
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
        cursor.execute(
            "INSERT INTO simulaciones (empresa, fecha, costo_total) VALUES (?, ?, ?)",
            (empresa, datetime.now().strftime("%Y-%m-%d %H:%M"), total)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "costo_total": round(total, 2),
            "arancel_calculado": round(arancel, 2),
            "iva_calculado": round(iva, 2),
            "cif": round(cif, 2),
            "success": True
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error en simulación: {str(e)}",
            "success": False
        }), 500

# ------------------------------
# HISTORIAL
# ------------------------------
@app.route('/historial', methods=['GET'])
def historial():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT empresa, fecha, costo_total 
        FROM simulaciones 
        ORDER BY id DESC 
        LIMIT 10
    """)
    
    resultados = cursor.fetchall()
    conn.close()
    
    return jsonify([
        {"empresa": r[0], "fecha": r[1], "costo_total": r[2]}
        for r in resultados
    ])

# ------------------------------
# LIMPIAR CACHE
# ------------------------------
@app.route('/limpiar-cache', methods=['POST'])
def limpiar_cache():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM aranceles_cache")
    conn.commit()
    conn.close()
    
    return jsonify({"mensaje": "Cache limpiado", "success": True})

# ------------------------------
# RUN
# ------------------------------
if __name__ == '__main__':
    app.run(port=5000, debug=True)
