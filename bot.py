import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, ChatJoinRequestHandler, ContextTypes

TOKEN = "8860001138:AAEx-64_E90wzmDJEEKRsS6IDgGJ-NwyIQw"

# Render ve UptimeRobot için sahte web sunucusu
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot 7/24 Aktif ve Calisiyor!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()

async def katilma_istegi_yakala(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kullanici = update.chat_join_request.from_user
    kullanici_adi = kullanici.first_name
    print(f"Yeni katılma isteği geldi: {kullanici_adi}")

def main():
    print("Hoş Geldin Botu başarıyla çalışıyor! Beklemedeyim...")
    
    # Sahte web sunucusunu arka planda başlatıyoruz ki Render hata vermesin
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatJoinRequestHandler(katilma_istegi_yakala))
    app.run_polling()

if __name__ == '__main__':
    main()
