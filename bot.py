import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ChatMemberHandler, ContextTypes

TOKEN = "8860001138:AAEx-64_E90wzmDJEEKRsS6IDgGJ-NwyIQw"

# Render ve UptimeRobot için sahte web sunucusu
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Karsilama Botu Aktif!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()

async def yeni_uye_Karsila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    # Üyenin gruba katılıp katılmadığını kontrol et
    yeni_durum = result.new_chat_member.status
    eski_durum = result.old_chat_member.status

    if eski_durum in ["left", "banned"] and yeni_durum in ["member", "administrator"]:
        kullanici = result.new_chat_member.user
        kullanici_adi = kullanici.first_name
        username = f"@{kullanici.username}" if kullanici.username else f"[{kullanici_adi}](tg://user?id={kullanici.id})"
        
        chat = result.chat
        toplam_uye = await chat.get_member_count()

        # Kurallar Butonu ve Uyarısı
        kurallar_url = "https://telegra.ph/Grup-Kurallar%C4%B1-09-27"
        buton = [[InlineKeyboardButton("📋 KURALLAR", url=kurallar_url)]]
        reply_markup = InlineKeyboardMarkup(buton)

        mesaj = (
            f"Aramıza hoş geldin {username}! Seninle birlikte artık {toplam_uye} kişi olduk!\n\n"
            f"‼️Kurallara uymayan uyarılmadan gruptan çıkarılır‼️"
        )

        await context.bot.send_message(
            chat_id=chat.id,
            text=mesaj,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # Yeni üyeleri yakalamak için handler ekliyoruz
    app.add_handler(ChatMemberHandler(yeni_uye_Karsila, ChatMemberHandler.CHAT_MEMBER))
    
    app.run_polling()

if __name__ == '__main__':
    main()
