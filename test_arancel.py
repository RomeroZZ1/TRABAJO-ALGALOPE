import pdfplumber
import re
import sqlite3
import os

pdf_path = r"C:\Users\Nicolas Romero Diaz\OneDrive\Documentos\TRABAJO ALGALOPE\decreto_1881_2021.pdf"
db_path = "database.db"

def extraccion_profunda():
    if not os.path.exists(pdf_path):
        print("❌ Archivo no encontrado.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS aranceles_cache")
    cursor.execute("CREATE TABLE aranceles_cache (partida TEXT PRIMARY KEY, designacion TEXT, gravamen REAL)")

    print("🚀 Iniciando extracción profunda de TODAS las partidas...")
    
    conteo = 0
    with pdfplumber.open(pdf_path) as pdf:
        for i, pagina in enumerate(pdf.pages):
            # Extraemos la tabla de forma estructurada
            tabla = pagina.extract_table()
            
            if tabla:
                for fila in tabla:
                    # Una fila válida debe tener el código en la primera columna
                    # Formato: 0101.21.00.00
                    if fila[0] and re.match(r'\d{4}\.\d{2}\.\d{2}\.\d{2}', str(fila[0])):
                        try:
                            codigo = str(fila[0]).replace(".", "").strip()
                            # La descripción suele estar en la columna 1 y el gravamen en la 2 o 3
                            designacion = str(fila[1]).replace("\n", " ").strip()
                            
                            # Buscamos el gravamen: recorremos la fila desde el final hasta encontrar un número
                            gravamen = None
                            for celda in reversed(fila):
                                if celda and str(celda).strip().isdigit():
                                    gravamen = float(celda)
                                    break
                            
                            if gravamen is not None:
                                cursor.execute("INSERT OR IGNORE INTO aranceles_cache VALUES (?, ?, ?)", 
                                             (codigo, designacion, gravamen))
                                conteo += 1
                        except:
                            continue
            
            if i % 50 == 0:
                print(f"⏳ Procesadas {i} páginas... Registros: {conteo}")

    conn.commit()
    conn.close()
    print(f"\n✅ ¡Éxito! Ahora tienes {conteo} partidas reales en tu base de datos.")

if __name__ == "__main__":
    extraccion_profunda()