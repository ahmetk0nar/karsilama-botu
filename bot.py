import os
import json
import logging
import threading
from io import BytesIO
from datetime import datetime, time
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# =========================================================
# AYARLAR
# =========================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

VERI_DOSYASI = "uyeler.json"
ARKA_PLAN_DOSYASI = "arkaplan.jpg"

# YENİ KURALLAR LİNKİN
KURALLAR_URL = "https://telegra.ph/GRUP-KURALLARI-09-28"

ISTANBUL = ZoneInfo("Europe/Istanbul")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RENDER SAĞLIK SUNUCUSU
# =========================================================

class DummyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            "Karşılama Botu Aktif!".encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def run_dummy_server():

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    server_address = (
        "0.0.0.0",
        port
    )

    httpd = HTTPServer(
        server_address,
        DummyHandler
    )

    httpd.serve_forever()


# =========================================================
# VERİTABANI / JSON
# =========================================================

def verileri_yukle():

    if not os.path.exists(VERI_DOSYASI):
        return {}

    try:

        with open(
            VERI_DOSYASI,
            "r",
            encoding="utf-8"
        ) as f:

            veri = json.load(f)

            if isinstance(veri, dict):
                return veri

            return {}

    except Exception as e:

        logger.exception(
            "uyeler.json okunamadı: %s",
            e
        )

        return {}


def verileri_kaydet(veri):

    try:

        gecici = VERI_DOSYASI + ".tmp"

        with open(
            gecici,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                veri,
                f,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            gecici,
            VERI_DOSYASI
        )

    except Exception as e:

        logger.exception(
            "uyeler.json kaydedilemedi: %s",
            e
        )


def istanbul_simdi():

    return datetime.now(
        ISTANBUL
    )


# =========================================================
# FONT BULMA
# =========================================================

def font_bul(
    boyut,
    kalin=False
):

    if kalin:

        adaylar = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]

    else:

        adaylar = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]

    for yol in adaylar:

        try:

            if os.path.exists(yol):

                return ImageFont.truetype(
                    yol,
                    boyut
                )

        except Exception:
            pass

    return ImageFont.load_default()


def sigacak_isim_fontu(
    draw,
    metin,
    maksimum_genislik,
    baslangic=100,
    minimum=42
):

    boyut = baslangic

    while boyut >= minimum:

        font = font_bul(
            boyut,
            kalin=True
        )

        bbox = draw.textbbox(
            (0, 0),
            metin,
            font=font
        )

        if bbox[2] - bbox[0] <= maksimum_genislik:

            return font

        boyut -= 4

    return font_bul(
        minimum,
        kalin=True
    )


# =========================================================
# PROFİL FOTOĞRAFI VE AFİŞ
# =========================================================

async def profil_fotosunu_al(
    bot,
    user_id
):

    try:

        sonuc = await bot.get_user_profile_photos(
            user_id=user_id,
            limit=1
        )

        if (
            sonuc.total_count == 0
            or not sonuc.photos
        ):
            return None

        en_buyuk = sonuc.photos[0][-1]

        telegram_file = await bot.get_file(
            en_buyuk.file_id
        )

        bio = BytesIO()

        await telegram_file.download_to_memory(
            bio
        )

        return bio.getvalue()

    except Exception as e:

        logger.warning(
            "Profil fotosu alınamadı: %s",
            e
        )
        return None

def afis_olustur(profil_bytes, kullanici_adi):
    if os.path.exists(ARKA_PLAN_DOSYASI):
        bg = Image.open(ARKA_PLAN_DOSYASI).convert("RGBA")
        bg = bg.resize((800, 400))
    else:
        bg = Image.new("RGBA", (800, 400), (45, 45, 45, 255))

    draw = ImageDraw.Draw(bg)

    if profil_bytes:
        try:
            pfp = Image.open(BytesIO(profil_bytes)).convert("RGBA")
            pfp = pfp.resize((150, 150))
            mask = Image.new("L", (150, 150), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 150, 150), fill=255)
            pfp.putalpha(mask)
            bg.paste(pfp, (325, 50), pfp)
        except Exception as e:
            logger.error("Profil fotosu işlenemedi: %s", e)

    font = sigacak_isim_fontu(draw, kullanici_adi, 700, 60, 30)
    bbox = draw.textbbox((0, 0), kullanici_adi, font=font)
    x_pos = (800 - (bbox[2] - bbox[0])) / 2
    draw.text((x_pos, 220), kullanici_adi, fill="white", font=font)

    out = BytesIO()
    bg.convert("RGB").save(out, format="JPEG")
    out.seek(0)
    return out


# =========================================================
# BOT İŞLEMLERİ VE KOMUTLAR
# =========================================================

async def start_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Özelden start verilince çalışacak kısım
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Merhaba! Ben bir grup karşılama botuyum. Beni bir gruba ekleyip yönetici yaparsan "
            "yeni gelenleri harika şekilde karşılayabilirim!"
        )

async def yeni_uye_karsilama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    veri = verileri_yukle()
    chat_id_str = str(chat.id)

    if chat_id_str not in veri:
        veri[chat_id_str] = {}

    uye_sayisi = await chat.get_member_count()

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        # Kullanıcıyı veritabanına kaydet (Yıl dönümü için)
        user_id_str = str(member.id)
        veri[chat_id_str][user_id_str] = {
            "ad": member.first_name,
            "katilma_tarihi": istanbul_simdi().strftime("%Y-%m-%d")
        }

        # 1. Kullanıcıya Özel Karşılama ve Sayaç (DM üzerinden atılır, sadece o görür)
        ozel_mesaj = f"Aramıza hoş geldin {member.first_name}! Seninle birlikte artık {uye_sayisi} kişi olduk!"
        try:
            await context.bot.send_message(chat_id=member.id, text=ozel_mesaj)
        except Exception:
            pass # Eğer kullanıcı bota DM'den start vermemişse Telegram kuralı gereği DM atılamaz, hata vermesin diye pass geçiyoruz.

        # 2. Kullanıcıya Özel Afiş (DM üzerinden atılır)
        profil_bytes = await profil_fotosunu_al(context.bot, member.id)
        afis = afis_olustur(profil_bytes, member.first_name)
        try:
            await context.bot.send_photo(chat_id=member.id, photo=afis)
        except Exception:
            pass

        # 3. Herkese Görünür Grup Kuralları Mesajı (Grupta atılır)
        kurallar_butonu = InlineKeyboardMarkup([
            [InlineKeyboardButton("KURALLARA", url=KURALLAR_URL)]
        ])
        
        # Tam istediğin herkese görünür mesaj formatı
        genel_mesaj = f"@{member.username if member.username else member.first_name} HOŞ GELDİN! NASILSIN\n\n‼️Kurallara uymayan uyarılmadan gruptan çıkarılır‼️"
        
        await context.bot.send_message(
            chat_id=chat.id,
            text=genel_mesaj,
            reply_markup=kurallar_butonu
        )

    verileri_kaydet(veri)


async def yildonumu_kontrol(context: ContextTypes.DEFAULT_TYPE):
    veri = verileri_yukle()
    bugun = istanbul_simdi()
    bugun_ay_gun = bugun.strftime("%m-%d")

    for chat_id, uyeler in veri.items():
        for user_id, bilgiler in uyeler.items():
            katilma = bilgiler.get("katilma_tarihi")
            if katilma:
                if katilma[5:] == bugun_ay_gun and katilma[:4] != str(bugun.year):
                    try:
                        isim = bilgiler.get('ad', 'Üyemiz')
                        mesaj = f"🎉 Mutlu Yıl Dönümleri! {isim}, grubumuzdaki 1. yılını doldurdu!"
                        await context.bot.send_message(chat_id=int(chat_id), text=mesaj)
                    except Exception as e:
                        logger.error("Yıl dönümü mesajı gönderilemedi: %s", e)

def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN bulunamadı!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_komutu))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, yeni_uye_karsilama))

    app.job_queue.run_daily(yildonumu_kontrol, time=time(hour=10, minute=0, tzinfo=ISTANBUL))

    threading.Thread(target=run_dummy_server, daemon=True).start()

    logger.info("Bot başlatılıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
