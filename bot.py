import os
import threading
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ChatMemberHandler, ContextTypes
from PIL import Image, ImageDraw, ImageFont

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

# Kişiselleştirilmiş Karşılama Görseli (Banner) Üreten Fonksiyon
def banner_olustur(kullanici_adi):
    # 800x400 boyutunda şık koyu gri/mavi tonlarında bir arkaplan oluşturuyoruz
    genislik, yukseklik = 800, 400
    arkaplan_rengi = (20, 24, 33) # Koyu tema renk
    img = Image.new("RGB", (genislik, yukseklik), color=arkaplan_rengi)
    draw = ImageDraw.Draw(img)
    
    # Çerçeve ekleyelim
    draw.rectangle([15, 15, genislik - 15, yukseklik - 15], outline=(52, 152, 219), width=3)
    
    try:
        # Sistemde varsayılan kalın bir font bulmaya çalışalım, yoksa varsayılanı kullanır
        font_baslik = ImageFont.truetype("arial.ttf", 36)
        font_isim = ImageFont.truetype("arial.ttf", 44)
        font_alt = ImageFont.truetype("arial.ttf", 22)
    except:
        font_baslik = ImageFont.load_default()
        font_isim = ImageFont.load_default()
        font_alt = ImageFont.load_default()
        
    # Yazıları ortalayarak ekleyelim
    draw.text((genislik / 2, 80), "ARAMIZA HOŞ GELDİN", fill=(255, 255, 255), anchor="mm", font=font_baslik)
    draw.text((genislik / 2, 170), f"{kullanici_adi}", fill=(52, 152, 219), anchor="mm", font=font_isim)
    draw.text((genislik / 2, 260), "Topluluğumuzun yeni gücü sen de oldun!", fill=(189, 195, 199), anchor="mm", font=font_alt)
    draw.text((genislik / 2, 330), "‼️ Kurallara uymayan uyarılmadan gruptan çıkarılır ‼️", fill=(231, 76, 60), anchor="mm", font=font_alt)
    
    # Bellekte görseli bayt (bytes) formatına çeviriyoruz ki Telegram'a dosya olarak gönderebilelim
    bio = BytesIO()
    bio.name = 'hosgeldin.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

async def yeni_uye_Karsila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    yeni_durum = result.new_chat_member.status
    eski_durum = result.old_chat_member.status

    if eski_durum in ["left", "banned"] and yeni_durum in ["member", "administrator"]:
        kullanici = result.new_chat_member.user
        kullanici_adi = kullanici.first_name
        username = f"@{kullanici.username}" if kullanici.username else f"[{kullanici_adi}](tg://user?id={kullanici.id})"
        
        chat = result.chat
        toplam_uye = await chat.get_member_count()

        # Kurallar Butonu
        kurallar_url = "https://telegra.ph/Grup-Kurallar%C4%B1-09-27"
        buton = [[InlineKeyboardButton("📋 KURALLAR", url=kurallar_url)]]
        reply_markup = InlineKeyboardMarkup(buton)

        metin = (
            f"Aramıza hoş geldin {username}!\n"
            f"Seninle birlikte artık **{toplam_uye}** kişi olduk!\n\n"
            f"‼️ Kurallara uymayan uyarılmadan gruptan çıkarılır ‼️"
        )

        # 1. Kişiselleştirilmiş Banner Görselini Üret
        banner_dosyasi = banner_olustur(kullanici_adi)

        # 2. Görseli ve metni butonla birlikte gruba gönder
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=banner_dosyasi,
            caption=metin,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(yeni_uye_Karsila, ChatMemberHandler.CHAT_MEMBER))
    
    app.run_polling()

if __name__ == '__main__':
    main()
