import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont

# BURAYA BOTFATHER'DAN ALDIĞIN TOKEN'I YAPIŞTIR
TOKEN = "8860001138:AAEx-64_E90wzmDJEEKRsS6IDgGJ-NwyIQw"

async def karsilama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for yeni_uye in update.message.new_chat_members:
        # Eğer katılan kişi botun kendisiyse işlem yapma
        if yeni_uye.id == context.bot.id:
            continue

        uye_adi = yeni_uye.first_name
        uye_id = yeni_uye.id
        chat_id = update.message.chat_id

        # --- DİNAMİK ÜYE SAYACI ---
        uye_sayisi = await context.bot.get_chat_member_count(chat_id)

        # --- KİŞİSELLEŞTİRİLMİŞ KART (BANNER) ÜRETİMİ ---
        try:
            # Arkaplan resmini aç
            img = Image.open("arkaplan.jpg")
            draw = ImageDraw.Draw(img)
            
            # Yazı fontu ayarı (Varsayılan basit font)
            font = ImageFont.load_default()
            
            # Resmin üzerine yazı yazma (Şimdilik sol üst köşeye 50,50 koordinatına yazar)
            mesaj = f"Hos Geldin, {uye_adi}!"
            draw.text((50, 50), mesaj, fill="white", font=font)
            
            # Resmi bilgisayara kaydetmeden hafızada tut ve göndermeye hazırla
            resim_byte = io.BytesIO()
            img.save(resim_byte, format='JPEG')
            resim_byte.seek(0)
            
            # --- KİŞİSELLEŞTİRİLMİŞ KARŞILAMA MESAJI ---
            karsilama_metni = (
                f"Hoş geldin [{uye_adi}](tg://user?id={uye_id})! 🎉\n\n"
                f"Aramıza hoş geldin! Seninle birlikte artık {uye_sayisi} kişi olduk!"
            )
            
            # Resmi ve karşılama metnini gruba gönder
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=resim_byte,
                caption=karsilama_metni,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Resim oluşturulurken bir hata oldu: {e}")
            # Eğer resimde sorun çıkarsa (örneğin arkaplan.jpg bulunamazsa) sadece düz metin atar
            yedek_metin = f"Hoş geldin [{uye_adi}](tg://user?id={uye_id})! 🎉 Seninle birlikte artık {uye_sayisi} kişi olduk!"
            await context.bot.send_message(chat_id=chat_id, text=yedek_metin, parse_mode='Markdown')

        # --- GRUP KURALLARI PANELİ ---
        kurallar_metni = "‼️Kurallara uymayan uyarılmadan gruptan çıkarılır‼️"
        butonlar = [[InlineKeyboardButton("KURALLAR", url="https://telegra.ph/Grup-Kurallar%C4%B1-09-27")]]
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=kurallar_metni,
            reply_markup=InlineKeyboardMarkup(butonlar)
        )
        
        # Dönemsel kutlamalar (1. yıl vb.) için kullanıcının giriş tarihini 
        # veritabanına kaydetme kodları gelecekte buraya eklenecektir.

def main():
    # Botu başlat
    app = Application.builder().token(TOKEN).build()

    # Gruba yeni biri katıldığında 'karsilama' fonksiyonunu çalıştır
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, karsilama))

    print("Hoş Geldin Botu başarıyla çalışıyor! Beklemedeyim...")
    app.run_polling()

if __name__ == '__main__':
    main()