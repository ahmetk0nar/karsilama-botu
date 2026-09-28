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
# PROFİL FOTOĞRAFI
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

        logger.warning
