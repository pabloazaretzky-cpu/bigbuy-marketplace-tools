import ftplib
import os
from pathlib import Path

FTP_HOST = os.environ.get('FTP_HOST', 'TU_SERVIDOR_FTP')
FTP_USER = os.environ.get('FTP_USER', 'TU_USUARIO_FTP')
FTP_PASS = os.environ.get('FTP_PASS', 'TU_PASSWORD_FTP')
ARCHIVO_REMOTO = "/files/products/csv/standard/product_2399_es.csv"
ARCHIVO_LOCAL  = str(Path(__file__).parent / 'product_2399_es.csv')

def descargar_final():
    try:
        print("🔗 Conectando con las nuevas credenciales...")
        ftp = ftplib.FTP(FTP_HOST, timeout=60) # 60 segundos de espera
        ftp.login(FTP_USER, FTP_PASS)
        ftp.set_pasv(True) # Modo pasivo para evitar bloqueos de firewall
        
        print(f"📥 Descargando archivo grande... No cierres la ventana.")
        with open(ARCHIVO_LOCAL, 'wb') as f:
            ftp.retrbinary(f"RETR {ARCHIVO_REMOTO}", f.write)
            
        ftp.quit()
        print(f"✅ ¡LO LOGRAMOS! Archivo guardado en {ARCHIVO_LOCAL}")
    except Exception as e:
        print(f"❌ Error con las nuevas credenciales: {e}")

if __name__ == "__main__":
    descargar_final()