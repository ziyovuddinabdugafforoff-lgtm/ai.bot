import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ChatAction, ParseMode
from dotenv import load_dotenv
import google.generativeai as genai

# ============================================================
#  SOZLAMALAR
# ============================================================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi. Railway 'Variables' bo'limini tekshiring.")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY topilmadi. Railway 'Variables' bo'limini tekshiring.")

logging.basicConfig(level=logging.INFO)

genai.configure(api_key=GEMINI_API_KEY)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

SYSTEM_PROMPT = (
    "Siz professional, bilimdon va foydali sun'iy intellekt yordamchisisiz. "
    "Savollarga chuqur, aniq va tuzilgan tarzda javob bering. "
    "Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob bering. "
    "Agar savol Uzum Market, Wildberries yoki Xitoydan tovar buyurtma qilish bilan bog'liq bo'lsa, "
    "amaliy va foydali maslahatlar bering."
)

gemini_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=SYSTEM_PROMPT,
)

# Har bir foydalanuvchi uchun AI suhbat sessiyasi (xotirada)
user_chats: dict[int, "genai.ChatSession"] = {}

# ============================================================
#  MENYU TUGMALARI
# ============================================================
BTN_AI = "🤖 AI bilan suhbat"
BTN_MARKET = "🛒 Uzum va Wildberries savdosi"
BTN_CHINA = "🇨🇳 Xitoydan tovar buyurtma"
BTN_ADS = "📢 Reklama va Hamkorlik"
BTN_ABOUT = "ℹ️ Bot haqida"
BTN_BACK = "⬅️ Bosh menyu"

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_AI)],
        [KeyboardButton(text=BTN_MARKET), KeyboardButton(text=BTN_CHINA)],
        [KeyboardButton(text=BTN_ADS), KeyboardButton(text=BTN_ABOUT)],
    ],
    resize_keyboard=True,
)

back_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_BACK)]],
    resize_keyboard=True,
)

user_mode: dict[int, str] = {}

# ============================================================
#  STATIK MATNLAR
# ============================================================

WELCOME_TEXT = (
    "👋 <b>Xush kelibsiz!</b>\n\n"
    "Bu — sun'iy intellekt asosida ishlaydigan professional yordamchi bot.\n\n"
    "Quyidagi bo'limlardan birini tanlang:\n\n"
    f"{BTN_AI} — istalgan mavzuda, hatto murakkab savollarga ham AI orqali javob oling\n"
    f"{BTN_MARKET} — Uzum Market va Wildberries'da savdo qilish bo'yicha amaliy ma'lumot\n"
    f"{BTN_CHINA} — Xitoydan tovar buyurtma qilish (Alibaba, 1688, Taobao)\n"
    f"{BTN_ADS} — Reklama joylashtirish va hamkorlik\n"
    f"{BTN_ABOUT} — Bot imkoniyatlari haqida"
)

ABOUT_TEXT = (
    "ℹ️ <b>Bot haqida</b>\n\n"
    "Bu bot sun'iy intellekt (Google Gemini) asosida ishlaydi va quyidagilarni bajara oladi:\n\n"
    "• Istalgan mavzuda murakkab savollarga chuqur, tahliliy javob berish\n"
    "• Matn yozish, tarjima qilish, tushuntirish, kod yozish\n"
    "• Har bir foydalanuvchi bilan alohida suhbat tarixini eslab qolish\n"
    "• Uzum/Wildberries va Xitoy savdosi bo'yicha maxsus bo'limlar\n\n"
    "Bot bir vaqtning o'zida ko'plab foydalanuvchilarga xizmat ko'rsatishga mo'ljallangan."
)

ADS_TEXT = (
    "📢 <b>Reklama va Hamkorlik</b>\n\n"
    "Ushbu botda reklama joylashtirish, hamkorlik yoki xizmatlar bo'yicha "
    "murojaat qilish uchun quyidagi kontaktlardan foydalaning:\n\n"
    "📞 Telefon: <code>+998997347704</code>\n"
    "💬 Telegram: @ziyovuddin_abdugafforov\n\n"
    "Savol, taklif yoki hamkorlik bo'yicha bemalol murojaat qiling."
)

CHINA_TEXT = (
    "🇨🇳 <b>Xitoydan tovar buyurtma qilish</b>\n\n"
    "<b>Asosiy platformalar:</b>\n"
    "• <b>1688.com</b> — Xitoy ichki bozori, eng past narxlar, lekin faqat xitoy tilida va "
    "ko'pincha ulgurji (minimal miqdor talab qilinadi)\n"
    "• <b>Alibaba.com</b> — xalqaro ulgurji savdo, ingliz tilida, yetkazib beruvchi bilan "
    "to'g'ridan-to'g'ri muzokara qilish mumkin\n"
    "• <b>Taobao.com</b> — chakana (dona-dona) xarid uchun qulay, lekin yetkazib berish "
    "vositachi orqali bo'ladi\n\n"
    "<b>Muhim jihatlar:</b>\n"
    "• Birinchi marta buyurtma qilishdan oldin sotuvchining reytingi va sharhlarini tekshiring\n"
    "• Yetkazib berish odatda karyer (vositachi kompaniya) orqali amalga oshiriladi — "
    "og'irlik/hajm bo'yicha to'lov hisoblanadi\n"
    "• Bojxona qoidalari va bepul limit miqdorini oldindan bilib oling — bu doimiy o'zgarib turadi, "
    "shuning uchun buyurtma berishdan oldin joriy holatni tekshirish tavsiya etiladi\n"
    "• Namuna (sample) so'rab, sifatni tekshirgandan keyin katta miqdorda buyurtma bering\n\n"
    "Aniq mahsulot yoki yetkazib berish narxi bo'yicha savolingiz bo'lsa, "
    f"'{BTN_AI}' bo'limiga yozing — batafsil maslahat beraman."
)

MARKET_TEXT = (
    "🛒 <b>Uzum Market va Wildberries'da savdo qilish</b>\n\n"
    "<b>Boshlashdan oldin bilishingiz kerak bo'lgan amaliy jihatlar:</b>\n\n"
    "1️⃣ <b>Komissiya va xarajatlarni oldindan hisoblang</b>\n"
    "Platforma komissiyasi, yetkazib berish, qadoqlash va qaytarish (vozvrat) xarajatlarini "
    "narxga qo'shmasangiz, ko'p sotuvchilar aylanma katta bo'lsa ham foyda ko'rmay qoladi.\n\n"
    "2️⃣ <b>Qaytarish (vozvrat) foizi — yashirin xarajat</b>\n"
    "Ayniqsa kiyim-kechak kategoriyasida qaytarish foizi juda yuqori bo'lishi mumkin — "
    "buni oldindan hisobga olmagan sotuvchilar zarar ko'radi.\n\n"
    "3️⃣ <b>Kartochka (mahsulot sahifasi) sifati sotuvni hal qiladi</b>\n"
    "Sifatli rasm, to'liq tavsif va kalit so'zlar bilan optimallashtirish qidiruvda yuqori "
    "chiqishga bevosita ta'sir qiladi — bu ko'pincha e'tiborga olinmaydi.\n\n"
    "4️⃣ <b>Reyting va sharhlar boshida sekin o'sadi</b>\n"
    "Yangi kartochkalar boshida kam ko'rinadi — birinchi sotuvlar va sharhlarni tez to'plash "
    "uchun boshlang'ich bosqichda narxni biroz pasaytirish strategiyasi ko'p qo'llaniladi.\n\n"
    "5️⃣ <b>Ombor (sklad) tanlovi muhim</b>\n"
    "Platformaning o'z omboriga tovar joylashtirish (FBO turi) tez yetkazib berish tufayli "
    "ko'pincha ko'proq sotuvga olib keladi, lekin saqlash xarajati bor — buni solishtirib ko'ring.\n\n"
    "⚠️ Narxlar, komissiya foizlari va qoidalar platformalarda tez-tez yangilanib turadi — "
    "aniq amaldagi shartlarni har doim platformaning rasmiy kabinetidan tekshiring.\n\n"
    f"Aniq mahsulot yoki strategiya bo'yicha maslahat kerak bo'lsa, '{BTN_AI}' bo'limiga yozing."
)

AI_INTRO = (
    "🤖 <b>AI suhbat rejimi yoqildi</b>\n\n"
    "Endi istalgan savolingizni yozing — oddiy suhbatdan tortib, murakkab tahliliy "
    "savollargacha, batafsil javob beraman.\n\n"
    f"Chiqish uchun '{BTN_BACK}' tugmasini bosing."
)


# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================
def get_chat_session(user_id: int) -> "genai.ChatSession":
    if user_id not in user_chats:
        user_chats[user_id] = gemini_model.start_chat(history=[])
    return user_chats[user_id]


async def ask_gemini(user_id: int, text: str) -> str:
    chat = get_chat_session(user_id)
    try:
        response = await asyncio.to_thread(chat.send_message, text)
        return response.text.strip()
    except Exception:
        logging.exception("Gemini API xatosi")
        return "⚠️ Kechirasiz, javob berishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."


# ============================================================
#  HANDLERLAR
# ============================================================
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_mode[message.from_user.id] = "free"
    user_chats.pop(message.from_user.id, None)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu, parse_mode=ParseMode.HTML)


@router.message(F.text == BTN_BACK)
async def go_back(message: Message) -> None:
    user_mode[message.from_user.id] = "free"
    await message.answer("Bosh menyuga qaytdingiz.", reply_markup=main_menu)


@router.message(F.text == BTN_ABOUT)
async def show_about(message: Message) -> None:
    await message.answer(ABOUT_TEXT, reply_markup=main_menu, parse_mode=ParseMode.HTML)


@router.message(F.text == BTN_ADS)
async def show_ads(message: Message) -> None:
    await message.answer(ADS_TEXT, reply_markup=main_menu, parse_mode=ParseMode.HTML)


@router.message(F.text == BTN_CHINA)
async def show_china(message: Message) -> None:
    await message.answer(CHINA_TEXT, reply_markup=main_menu, parse_mode=ParseMode.HTML)


@router.message(F.text == BTN_MARKET)
async def show_market(message: Message) -> None:
    await message.answer(MARKET_TEXT, reply_markup=main_menu, parse_mode=ParseMode.HTML)


@router.message(F.text == BTN_AI)
async def start_ai_mode(message: Message) -> None:
    user_mode[message.from_user.id] = "ai"
    user_chats.pop(message.from_user.id, None)
    await message.answer(AI_INTRO, reply_markup=back_menu, parse_mode=ParseMode.HTML)


@router.message(F.text)
async def handle_free_text(message: Message) -> None:
    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    reply = await ask_gemini(user_id, message.text)
    keyboard = back_menu if user_mode.get(user_id) == "ai" else main_menu
    await message.answer(reply, reply_markup=keyboard)


# ============================================================
#  ISHGA TUSHIRISH
# ============================================================
async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
