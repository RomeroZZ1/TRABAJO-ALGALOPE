import pdfplumber
import re
import sqlite3

def extraccion_profesional():
    # Conexión con soporte para caracteres especiales
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS aranceles_cache")
    cursor.execute("""
        CREATE TABLE aranceles_cache (
            partida TEXT PRIMARY KEY, 
            designacion TEXT, 
            gravamen REAL
        )
    """)

    print("🚀 Iniciando extracción total. Por favor, no cierres el programa...")

    with pdfplumber.open("decreto_1881_2021.pdf") as pdf:
        conteo = 0
        for i, pagina in enumerate(pdf.pages):
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    if not fila or len(fila) < 2: continue
                    
                    # Limpiar código de partida (ej: 0101.21.00.00 -> 0101210000)
                    codigo = str(fila[0]).replace(".", "").strip()
                    
                    if len(codigo) == 10 and codigo.isdigit():
                        try:
                            # Corregir tildes y eñes
                            designacion = str(fila[1]).encode('latin-1').decode('utf-8', 'ignore')
                            designacion = designacion.replace("\n", " ").strip()
                            
                            # Buscar gravamen (suele estar en la columna 2 o 3)
                            gravamen = 0.0
                            for celda in fila[2:]:
                                if celda:
                                    num = str(celda).strip().replace("%", "").replace(",", ".")
                                    try:
                                        gravamen = float(num)
                                        break
                                    except: continue
                            
                            cursor.execute("INSERT OR IGNORE INTO aranceles_cache VALUES (?, ?, ?)", 
                                         (codigo, designacion, gravamen))
                            conteo += 1
                        except:
                            continue
            
            # Guardar progreso parcial cada 5 páginas para evitar pérdida de datos
            if i % 5 == 0:
                conn.commit()
                if i % 50 == 0:
                    print(f"✅ Página {i}... Partidas acumuladas: {conteo}")

    conn.commit()
    conn.close()
    print(f"\n✨ ¡PROCESO COMPLETADO! Se guardaron {conteo} partidas en database.db")

if __name__ == "__main__":
    extraccion_profesional()