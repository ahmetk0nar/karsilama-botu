import os
import json
import html
import logging
import threading
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# =========================
# AYARLAR
# =========================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VERI_DOSYASI = "uyeler.json"
ARKA_PLAN_DOSYASI = "arkaplan.jpg"
KURALLAR_URL = "https://telegra.ph/Grup-Kurallar%C4%B1-09-27"
ISTANBUL = ZoneInfo("Europe/Istanbul")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# =========================
# RENDER ICIN SAGLIK SUNUCUSU
# =========================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Karşılama Botu Aktif!".encode("utf-8"))

    def log_message(self, format, *args):
        return


def run_dummy_server():
    port = int(os.environ.get("PORT", "10000"))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()


# =========================
# VERI ISLEMLERI
# =========================
def verileri_yukle():
    if not os.path.exists(VERI_DOSYASI):
        return {}

    try:
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
            return veri if isinstance(veri, dict) else {}
    except Exception as e:
        logger.exception("uyeler.json okunamadı: %s", e)
        return {}


def verileri_kaydet(veri):
    try:
        gecici = VERI_DOSYASI + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=4)
        os.replace(gecici, VERI_DOSYASI)
    except Exception as e:
        logger.exception("uyeler.json kaydedilemedi: %s", e)


def istanbul_simdi():
    return datetime.now(ISTANBUL)


# =========================
# FONT BULMA
# Render + Windows uyumlu
# =========================
def font_bul(boyut, kalin=False):
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
                return ImageFont.truetype(yol, boyut)
        except Exception:
            pass

    # Son çare: Pillow varsayılan fontu.
    return ImageFont.load_default()


def sigacak_isim_fontu(draw, metin, maksimum_genislik, baslangic=100, minimum=42):
    boyut = baslangic
    while boyut >= minimum:
        font = font_bul(boyut, kalin=True)
        bbox = draw.textbbox((0, 0), metin, font=font)
        if bbox[2] - bbox[0] <= maksimum_genislik:
            return font
        boyut -= 4
    return font_bul(minimum, kalin=True)


# =========================
# PROFIL FOTOGRAFI
# =========================
async def profil_fotosunu_al(bot, user_id):
    try:
        sonuc = await bot.get_user_profile_photos(user_id=user_id, limit=1)
        if sonuc.total_count == 0 or not sonuc.photos:
            return None

        en_buyuk = sonuc.photos[0][-1]
        telegram_file = await bot.get_file(en_buyuk.file_id)

        bio = BytesIO()
        await telegram_file.download_to_memory(bio)
        return bio.getvalue()
    except Exception as e:
        logger.warning("%s kullanıcısının profil fotoğrafı alınamadı: %s", user_id, e)
        return None


# =========================
# BANNER OLUSTURMA
# =========================
def banner_olustur(kullanici_adi, toplam_uye, profil_foto=None):
    genislik, yukseklik = 1600, 900

    # Arka plan
    if os.path.exists(ARKA_PLAN_DOSYASI):
        try:
            arka_plan = Image.open(ARKA_PLAN_DOSYASI).convert("RGB")
            arka_plan = ImageOps.fit(
                arka_plan,
                (genislik, yukseklik),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            arka_plan = ImageEnhance.Brightness(arka_plan).enhance(0.42)
            img = arka_plan.convert("RGBA")
        except Exception as e:
            logger.warning("Arka plan açılamadı: %s", e)
            img = Image.new("RGBA", (genislik, yukseklik), (20, 24, 33, 255))
    else:
        img = Image.new("RGBA", (genislik, yukseklik), (20, 24, 33, 255))

    # Koyu katman: yazının okunurluğu artsın.
    karartma = Image.new("RGBA", (genislik, yukseklik), (0, 0, 0, 90))
    img = Image.alpha_composite(img, karartma)

    draw = ImageDraw.Draw(img)

    # Dış çerçeve
    draw.rounded_rectangle(
        [22, 22, genislik - 22, yukseklik - 22],
        radius=30,
        outline=(52, 152, 219, 230),
        width=5,
    )

    # Profil fotoğrafı alanı
    avatar_size = 290
    avatar_x = 120
    avatar_y = 275

    if profil_foto:
        try:
            avatar = Image.open(BytesIO(profil_foto)).convert("RGB")
            avatar = ImageOps.fit(
                avatar,
                (avatar_size, avatar_size),
                method=Image.Resampling.LANCZOS,
            )

            # Hafif gölge
            shadow = Image.new("RGBA", (avatar_size + 26, avatar_size + 26), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.ellipse(
                [10, 10, avatar_size + 10, avatar_size + 10],
                fill=(0, 0, 0, 150),
            )
            img.alpha_composite(shadow, (avatar_x - 4, avatar_y + 10))

            # Daire maske
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
            img.paste(avatar, (avatar_x, avatar_y), mask)

            # Beyaz/mavi çerçeve
            draw.ellipse(
                [avatar_x - 7, avatar_y - 7, avatar_x + avatar_size + 7, avatar_y + avatar_size + 7],
                outline=(255, 255, 255, 240),
                width=8,
            )
        except Exception as e:
            logger.warning("Profil fotoğrafı banner'a eklenemedi: %s", e)

    # Sağdaki metin alanı
    metin_merkez_x = 1030
    baslik_font = font_bul(64, kalin=True)
    isim_font = sigacak_isim_fontu(draw, kullanici_adi, 950, baslangic=110, minimum=46)
    alt_font = font_bul(40, kalin=False)
    sayac_font = font_bul(48, kalin=True)
    uyari_font = font_bul(32, kalin=True)

    def ortali_metni_golgelendir(metin, xy, font, fill, stroke=0, stroke_fill=(0, 0, 0, 180)):
        draw.text(
            (xy[0] + 4, xy[1] + 4),
            metin,
            font=font,
            fill=(0, 0, 0, 190),
            anchor="mm",
            stroke_width=stroke,
            stroke_fill=stroke_fill,
        )
        draw.text(
            xy,
            metin,
            font=font,
            fill=fill,
            anchor="mm",
            stroke_width=stroke,
            stroke_fill=stroke_fill,
        )

    ortali_metni_golgelendir(
        "ARAMIZA HOŞ GELDİN",
        (metin_merkez_x, 150),
        baslik_font,
        (255, 255, 255, 255),
        stroke=2,
    )

    ortali_metni_golgelendir(
        kullanici_adi,
        (metin_merkez_x, 315),
        isim_font,
        (52, 152, 219, 255),
        stroke=3,
        stroke_fill=(0, 0, 0, 220),
    )

    ortali_metni_golgelendir(
        "Topluluğumuza katıldığın için mutluyuz!",
        (metin_merkez_x, 465),
        alt_font,
        (240, 243, 247, 255),
        stroke=1,
    )

    ortali_metni_golgelendir(
        f"Seninle birlikte artık {toplam_uye:,} kişiyiz!".replace(",", "."),
        (metin_merkez_x, 555),
        sayac_font,
        (255, 255, 255, 255),
        stroke=2,
    )

    # Alt uyarı paneli
    panel_y1, panel_y2 = 700, 820
    draw.rounded_rectangle(
        [90, panel_y1, genislik - 90, panel_y2],
        radius=24,
        fill=(0, 0, 0, 145),
        outline=(231, 76, 60, 235),
        width=3,
    )

    draw.text(
        (genislik / 2, (panel_y1 + panel_y2) / 2),
        "‼️ KURALLARA UYMAYANLAR UYARILMADAN GRUPTAN ÇIKARILIR ‼️",
        fill=(255, 225, 225, 255),
        font=uyari_font,
        anchor="mm",
        stroke_width=1,
        stroke_fill=(70, 0, 0, 230),
    )

    bio = BytesIO()
    bio.name = "hosgeldin.png"
    img.convert("RGB").save(bio, "PNG", optimize=True)
    bio.seek(0)
    return bio


# =========================
# EPHEMERAL (SADECE HEDEF KULLANICI GORUR)
# =========================
EPHEMERAL_API_KWARGS = lambda user_id: {
    "ephemeral_message_parameters": {
        "receiver_user_id": user_id
    }
}


async def yeni_uye_karsila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = update.message
    if not mesaj or not mesaj.new_chat_members:
        return

    chat = mesaj.chat

    try:
        toplam_uye = await context.bot.get_chat_member_count(chat.id)
    except Exception as e:
        logger.exception("Üye sayısı alınamadı: %s", e)
        toplam_uye = 0

    veriler = verileri_yukle()
    bugun_tarihi = istanbul_simdi().strftime("%Y-%m-%d")

    for kullanici in mesaj.new_chat_members:
        if kullanici.is_bot or kullanici.id == context.bot.id:
            continue

        user_id_str = str(kullanici.id)
        kayit_anahtari = f"{chat.id}:{user_id_str}"

        # Kullanıcıyı/yıl dönümünü kaydet.
        veriler[kayit_anahtari] = {
            "user_id": kullanici.id,
            "ad": kullanici.full_name,
            "username": kullanici.username,
            "katilis_tarihi": bugun_tarihi,
            "chat_id": chat.id,
        }
        verileri_kaydet(veriler)

        # 1) HERKESİN GÖRDÜĞÜ kurallar mesajı.
        kurallar_buton = [[
            InlineKeyboardButton("📋 KURALLAR", url=KURALLAR_URL)
        ]]

        await context.bot.send_message(
            chat_id=chat.id,
            text="‼️ Kurallara uymayan uyarılmadan gruptan çıkarılır ‼️",
            reply_markup=InlineKeyboardMarkup(kurallar_buton),
        )

        # 2) Profil fotoğrafını almaya çalış.
        profil_foto = await profil_fotosunu_al(context.bot, kullanici.id)

        # 3) SADECE YENİ ÜYENİN gördüğü karşılama mesajı.
        gorunen_ad = f"@{kullanici.username}" if kullanici.username else kullanici.first_name
        mention = f'<a href="tg://user?id={kullanici.id}">{html.escape(gorunen_ad)}</a>'

        metin = (
            f"👋 Aramıza hoş geldin {mention}!\n"
            f"👥 Seninle birlikte artık <b>{toplam_uye:,}</b> kişi olduk!\n\n"
            f"Topluluğumuza katıldığın için mutluyuz.\n"
            f"📋 Kurallara göz atmayı unutma."
        ).replace(",", ".")

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=metin,
                parse_mode="HTML",
                api_kwargs=EPHEMERAL_API_KWARGS(kullanici.id),
            )
        except Exception as e:
            # Özel mesaj başarısız olduysa herkese açık bir mesaj gönderme.
            # Böylece kullanıcıya özel olması gereken içerik yanlışlıkla gruba düşmez.
            logger.exception(
                "Ephemeral karşılama gönderilemedi. user_id=%s chat_id=%s: %s",
                kullanici.id,
                chat.id,
                e,
            )
            continue

        # 4) SADECE YENİ ÜYENİN gördüğü banner.
        try:
            banner = banner_olustur(
                kullanici_adi=kullanici.full_name,
                toplam_uye=toplam_uye,
                profil_foto=profil_foto,
            )

            await context.bot.send_photo(
                chat_id=chat.id,
                photo=banner,
                api_kwargs=EPHEMERAL_API_KWARGS(kullanici.id),
            )
        except Exception as e:
            logger.exception(
                "Ephemeral banner gönderilemedi. user_id=%s chat_id=%s: %s",
                kullanici.id,
                chat.id,
                e,
            )


# =========================
# YIL DONUMU KONTROLU
# =========================
async def yildonumu_kontrol(context: ContextTypes.DEFAULT_TYPE):
    veriler = verileri_yukle()
    simdi = istanbul_simdi()
    bugun = simdi.strftime("%m-%d")

    for _, bilgi in veriler.items():
        katilis_str = bilgi.get("katilis_tarihi")
        if not katilis_str:
            continue

        try:
            katilis_tarihi = datetime.strptime(katilis_str, "%Y-%m-%d").replace(tzinfo=ISTANBUL)
        except ValueError:
            continue

        if (
            katilis_tarihi.year < simdi.year
            and katilis_tarihi.strftime("%m-%d") == bugun
        ):
            chat_id = bilgi.get("chat_id")
            user_id = bilgi.get("user_id")
            isim = bilgi.get("ad", "Üyemiz")

            if not chat_id or not user_id:
                continue

            kutlama_mesaji = (
                f"🎉 <b>Harika bir gün!</b>\n\n"
                f"<a href=\"tg://user?id={user_id}\">{html.escape(isim)}</a> "
                f"kullanıcısının aramızdaki <b>{simdi.year - katilis_tarihi.year}. yıl dönümü!</b>\n\n"
                f"İyi ki varsın, topluluğumuza kattığın değer için teşekkür ederiz! 🚀"
            )

            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=kutlama_mesaji,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(
                    "Yıl dönümü mesajı gönderilemedi chat_id=%s user_id=%s: %s",
                    chat_id,
                    user_id,
                    e,
                )


# =========================
# HATA YAKALAYICI
# =========================
async def hata_yakala(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram güncellemesinde hata oluştu: %s", context.error)


# =========================
# BASLAT
# =========================
def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN bulunamadı. Render Environment Variables bölümüne "
            "TELEGRAM_BOT_TOKEN ekleyin."
        )

    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            yeni_uye_karsila,
        )
    )

    app.add_error_handler(hata_yakala)

    if app.job_queue:
        app.job_queue.run_repeating(
            yildonumu_kontrol,
            interval=86400,
            first=20,
        )
    else:
        logger.warning(
            "JobQueue aktif değil. requirements.txt içinde python-telegram-bot[job-queue] kullanın."
        )

    logger.info("Bot başlıyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
