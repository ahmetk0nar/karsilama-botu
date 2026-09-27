import os
import json
import threading
from io import BytesIO
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont

TOKEN = "8860001138:AAEx-64_E90wzmDJEEKRsS6IDgGJ-NwyIQw"
VERI_DOSYASI = "uyeler.json"

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

def verileri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def verileri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def banner_olustur(kullanici_adi):
    genislik, yukseklik = 800, 400
    arkaplan_rengi = (20, 24, 33)
    img = Image.new("RGB", (genislik, yukseklik), color=arkaplan_rengi)
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([15, 15, genislik - 15, yukseklik - 15], outline=(52, 152, 219), width=3)
    
    try:
        font_baslik = ImageFont.truetype("arial.ttf", 36)
        font_isim = ImageFont.truetype("arial.ttf", 44)
        font_alt = ImageFont.truetype("arial.ttf", 22)
    except:
        font_baslik = ImageFont.load_default()
        font_isim = ImageFont.load_default()
        font_alt = ImageFont.load_default()
        
    draw.text((genislik / 2, 80), "ARAMIZA HOŞ GELDİN", fill=(255, 255, 255), anchor="mm", font=font_baslik)
    draw.text((genislik / 2, 170), f"{kullanici_adi}", fill=(52, 152, 219), anchor="mm", font=font_isim)
    draw.text((genislik / 2, 260), "Topluluğumuzun yeni gücü sen de oldun!", fill=(189, 195, 199), anchor="mm", font=font_alt)
    draw.text((genislik / 2, 330), "‼️ Kurallara uymayan uyarılmadan gruptan çıkarılır ‼️", fill=(231, 76, 60), anchor="mm", font=font_alt)
    
    bio = BytesIO()
    bio.name = 'hosgeldin.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

async def yeni_uye_karsila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = update.message
    if not mesaj or not mesaj.new_chat_members:
        return

    chat = mesaj.chat
    toplam_uye = await chat.get_member_count()
    veriler = verileri_yukle()
    bugun_tarihi = datetime.now().strftime("%Y-%m-%d")

    for kullanici in mesaj.new_chat_members:
        if kullanici.id == context.bot.id:
            continue
            
        kullanici_adi = kullanici.first_name
        user_id_str = str(kullanici.id)
        username = f"@{kullanici.username}" if kullanici.username else f"[{kullanici_adi}](tg://user?id={kullanici.id})"

        veriler[user_id_str] = {
            "ad": kullanici_adi,
            "katilis_tarihi": bugun_tarihi,
            "chat_id": chat.id
        }
        verileri_kaydet(veriler)

        kurallar_url = "https://telegra.ph/Grup-Kurallar%C4%B1-09-27"
        buton = [[InlineKeyboardButton("📋 KURALLAR", url=kurallar_url)]]
        reply_markup = InlineKeyboardMarkup(buton)

        metin = (
            f"Aramıza hoş geldin {username}!\n"
            f"Seninle birlikte artık **{toplam_uye}** kişi olduk!\n\n"
            f"‼️ Kurallara uymayan uyarılmadan gruptan çıkarılır ‼️"
        )

        banner_dosyasi = banner_olustur(kullanici_adi)

        await context.bot.send_photo(
            chat_id=chat.id,
            photo=banner_dosyasi,
            caption=metin,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def yildonumu_kontrol(context: ContextTypes.DEFAULT_TYPE):
    veriler = verileri_yukle()
    bugun = datetime.now().strftime("%m-%d") 
    
    for user_id, bilgi in veriler.items():
        katilis_str = bilgi.get("katilis_tarihi") 
        if katilis_str:
            katilis_tarihi = datetime.strptime(katilis_str, "%Y-%m-%d")
            if katilis_tarihi.year < datetime.now().year and katilis_tarihi.strftime("%m-%d") == bugun:
                chat_id = bilgi.get("chat_id")
                isim = bilgi.get("ad")
                
                kutlama_mesaji = (
                    f"🎉 **Harika bir gün!** Bugün [{isim}](tg://user?id={user_id}) kullanıcısının aramızdaki **yıl dönümü!** "
                    f"İyi ki varsın, topluluğumuza kattığın değer için teşekkür ederiz! 🚀"
                )
                try:
                    await context.bot.send_message(chat_id=chat_id, text=kutlama_mesaji, parse_mode="Markdown")
                except:
                    pass

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    if app.job_queue:
        app.job_queue.run_repeating(yildonumu_kontrol, interval=86400, first=10)
    
    # Hatalı olan StatusUpdate sınıfı temizlendi, doğrudan filters kullanılıyor
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, yeni_uye_karsila))
    
    app.run_polling()

if __name__ == '__main__':
    main()
