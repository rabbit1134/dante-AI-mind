"""
🤖 ربات تلگرام هوشمند — نسخه کامل
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
قابلیت‌ها:
  ✅ هوش مصنوعی GPT-4 با حافظه مکالمه
  ✅ اخبار فوتبال (لالیگا + لیگ انگلیس)
  ✅ اخبار سیاسی جهان
  ✅ قیمت لحظه‌ای طلا و دلار
  ✅ خوش‌آمدگویی در گروه + پیام خصوصی به عضو جدید
  ✅ پاسخ در گروه (با منشن) و پیوی

نصب:
  pip install python-telegram-bot openai httpx python-dotenv

متغیرهای محیطی (.env):
  TELEGRAM_TOKEN     — از @BotFather
  OPENAI_API_KEY     — از platform.openai.com
  NEWS_API_KEY       — از newsapi.org (رایگان)
  GROUP_CHAT_ID      — آیدی گروه (مثال: -1001234567890)
"""

import os
import logging
import asyncio
from datetime import time as dtime

import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─── تنظیمات ─────────────────────────────────────────────────────────────────
load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY    = os.getenv("NEWS_API_KEY")
GROUP_CHAT_ID   = int(os.getenv("GROUP_CHAT_ID", "0"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

# تاریخچه مکالمه هر کاربر  { user_id: [{"role":..., "content":...}] }
chat_history: dict[int, list[dict]] = {}

SYSTEM_PROMPT = (
    "تو یک دستیار هوشمند فارسی‌زبان هستی که در تلگرام فعالیت می‌کنی. "
    "پاسخ‌هایت باید صمیمی، مختصر و مفید باشند. "
    "از ایموجی مناسب استفاده کن. "
    "اگر سوال فنی یا اطلاعاتی است دقیق پاسخ بده، اگر گفت‌وگوی عادی است دوستانه باش. "
    "اگر کسی پرسید سازنده‌ات کیه، یا چه کسی تو رو ساخته، یا درباره توسعه‌دهنده سوال کرد، "
    "باید بگی که سازنده این ربات یک برنامه‌نویس هستن که می‌تونن از طریق "
    "کانال تلگرام @mxdxvxl یا اینستاگرام @ghoul._.boy باهاشون در ارتباط باشن."
)


# ═══════════════════════════════════════════════════════════════════════════════
# 🧠  هوش مصنوعی (GPT-4 با حافظه)
# ═══════════════════════════════════════════════════════════════════════════════
async def ask_gpt(user_id: int, user_message: str) -> str:
    """ارسال پیام به GPT-4 و دریافت پاسخ با حافظه مکالمه"""
    if user_id not in chat_history:
        chat_history[user_id] = []

    chat_history[user_id].append({"role": "user", "content": user_message})

    # فقط ۲۰ پیام آخر (مدیریت توکن)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[user_id][-20:]

    try:
        response = await ai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        chat_history[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        logger.error(f"خطا در GPT: {e}")
        return "❌ متاسفم، الان مشکلی پیش اومد. لطفاً دوباره امتحان کن."


# ═══════════════════════════════════════════════════════════════════════════════
# 📰  اخبار
# ═══════════════════════════════════════════════════════════════════════════════
async def fetch_news(query: str, count: int = 5) -> list[dict]:
    """دریافت اخبار از NewsAPI با جستجوی آزاد"""
    url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": NEWS_API_KEY,
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": count,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        return r.json().get("articles", [])


async def fetch_headlines(category: str = "general", count: int = 5) -> list[dict]:
    """اخبار برتر بر اساس دسته‌بندی"""
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "category": category,
        "pageSize": count,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        return r.json().get("articles", [])


def build_news_text(articles: list[dict], title: str, emoji: str) -> str:
    """قالب‌بندی اخبار"""
    if not articles:
        return f"{emoji} *{title}*\n\nخبری یافت نشد\\."
    lines = [f"{emoji} *{title}*\n"]
    for i, a in enumerate(articles[:5], 1):
        t = (a.get("title") or "بدون عنوان")[:80].replace("*","").replace("[","").replace("]","").replace("(","").replace(")","")
        u = a.get("url", "")
        lines.append(f"{i}\\. [{t}]({u})")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 💰  قیمت طلا و دلار
# ═══════════════════════════════════════════════════════════════════════════════
async def fetch_prices() -> str:
    """دریافت قیمت دلار و طلا از API رایگان"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # قیمت دلار (EUR/USD, GBP/USD از frankfurter.app رایگان)
            fx_r = await client.get("https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY")
            fx = fx_r.json()

            # قیمت طلا از metals-api (یا fallback متن)
            # از metals.live (رایگان و بدون نیاز به API key)
            gold_r = await client.get("https://metals.live/api/spot")
            gold_data = gold_r.json()
            gold_usd = None
            for item in gold_data:
                if item.get("symbol") == "XAU":
                    gold_usd = item.get("price")
                    break

        usd_to_eur = fx.get("rates", {}).get("EUR", "N/A")
        usd_to_gbp = fx.get("rates", {}).get("GBP", "N/A")

        lines = ["💰 *قیمت‌های جهانی*\n"]
        lines.append(f"🇺🇸 ۱ دلار = `{usd_to_eur}` یورو")
        lines.append(f"🇬🇧 ۱ دلار = `{usd_to_gbp}` پوند")
        if gold_usd:
            lines.append(f"🥇 طلا \\(هر اونس\\) = `${gold_usd:,.2f}`")
        else:
            lines.append("🥇 طلا: اطلاعات موجود نیست")
        lines.append("\n_منبع: frankfurter\\.app و metals\\.live_")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"خطا در دریافت قیمت: {e}")
        return "❌ دریافت قیمت با خطا مواجه شد\\. دوباره امتحان کن\\."


# ═══════════════════════════════════════════════════════════════════════════════
# 📅  ارسال خودکار روزانه
# ═══════════════════════════════════════════════════════════════════════════════
async def job_daily_news(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال خودکار بسته اخبار روزانه به گروه"""
    if GROUP_CHAT_ID == 0:
        return
    try:
        # اخبار سیاسی
        pol = await fetch_headlines("general", 4)
        pol_text = build_news_text(pol, "اخبار مهم جهان", "🌍")

        # اخبار فوتبال
        foot = await fetch_news("La Liga OR Premier League football", 4)
        foot_text = build_news_text(foot, "اخبار فوتبال", "⚽")

        # قیمت‌ها
        prices = await fetch_prices()

        full = f"{pol_text}\n\n{foot_text}\n\n{prices}"
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=full,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
        logger.info("بسته خبری روزانه ارسال شد ✅")
    except Exception as e:
        logger.error(f"خطا در ارسال روزانه: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎛️  دستورات
# ═══════════════════════════════════════════════════════════════════════════════
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚽ لالیگا", callback_data="news_laliga"),
            InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 لیگ انگلیس", callback_data="news_premier"),
        ],
        [
            InlineKeyboardButton("🌍 اخبار سیاسی", callback_data="news_politics"),
            InlineKeyboardButton("💰 طلا و دلار", callback_data="prices"),
        ],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")],
    ])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name
    chat_type = update.effective_chat.type

    if chat_type == "private":
        text = (
            f"سلام {name} عزیز! 👋\n\n"
            "خوش اومدی به ربات هوشمند من 🤖\n\n"
            "می‌تونم:\n"
            "• 💬 به سوالاتت پاسخ بدم \\(GPT\\-4\\)\n"
            "• ⚽ آخرین اخبار فوتبال رو بیارم\n"
            "• 🌍 اخبار سیاسی جهان رو نشون بدم\n"
            "• 💰 قیمت طلا و دلار رو بگم\n\n"
            "یه گزینه انتخاب کن یا هر چیزی می‌خوای بپرس\\! 😊"
        )
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=main_keyboard()
        )
    else:
        await update.message.reply_text(
            f"سلام {name}! 👋 منو منشن کن تا کمکت کنم 🤖",
        )


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی اخبار"""
    await update.message.reply_text(
        "📰 کدوم دسته‌بندی؟",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚽ لالیگا", callback_data="news_laliga"),
                InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 لیگ انگلیس", callback_data="news_premier"),
            ],
            [
                InlineKeyboardButton("🌍 اخبار سیاسی", callback_data="news_politics"),
                InlineKeyboardButton("⚡ همه اخبار", callback_data="news_all"),
            ],
        ])
    )


async def cmd_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ در حال دریافت قیمت‌ها...")
    text = await fetch_prices()
    await msg.edit_text(text, parse_mode="MarkdownV2")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    chat_history.pop(uid, None)
    await update.message.reply_text("🗑️ حافظه مکالمه پاک شد. از صفر شروع می‌کنیم!")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *راهنمای ربات*\n\n"
        "*در پیوی:* مستقیم پیام بده\n"
        "*در گروه:* منشنم کن: `@ربات سوالت`\n\n"
        "دستورات:\n"
        "/news — منوی اخبار\n"
        "/prices — قیمت طلا و دلار\n"
        "/clear — پاک کردن حافظه\n"
        "/help — راهنما",
        parse_mode="Markdown",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 💬  پیام‌های متنی → GPT
# ═══════════════════════════════════════════════════════════════════════════════
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    chat_type = update.effective_chat.type
    bot_username = (await context.bot.get_me()).username
    user_text = msg.text

    # ── در گروه: فقط وقتی منشن شده یا ریپلای روی پیام ربات ──
    if chat_type in ("group", "supergroup"):
        mentioned = f"@{bot_username}" in user_text
        replied_to_bot = (
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.username == bot_username
        )
        if not mentioned and not replied_to_bot:
            return
        # حذف منشن از متن
        user_text = user_text.replace(f"@{bot_username}", "").strip()

    if not user_text:
        return

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    reply = await ask_gpt(update.effective_user.id, user_text)
    await msg.reply_text(reply)


# ═══════════════════════════════════════════════════════════════════════════════
# 👋  خوش‌آمدگویی عضو جدید
# ═══════════════════════════════════════════════════════════════════════════════
async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """خوش‌آمدگویی در گروه + پیام خصوصی به عضو جدید"""
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        name = member.first_name
        user_id = member.id

        # ── ۱. خوش‌آمد در گروه ──
        group_name = update.effective_chat.title or "گروه"
        await update.message.reply_text(
            f"🎉 خوش اومدی {name} عزیز به *{group_name}*\\!\n\n"
            "امیدواریم اینجا وقت خوبی داشته باشی 😊\n"
            "هر وقت سوالی داشتی منو منشن کن 🤖",
            parse_mode="MarkdownV2",
        )

        # ── ۲. پیام خصوصی به عضو جدید ──
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"سلام {name} عزیز! 👋\n\n"
                    f"خوش اومدی به *{group_name}*\\!\n\n"
                    "من ربات هوشمند گروهم 🤖\n"
                    "می‌تونی اینجا توی پیوی باهام صحبت کنی، "
                    "سوال بپرسی، اخبار بگیری یا قیمت طلا و دلار چک کنی\\.\n\n"
                    "برای شروع /start رو بزن\\! 😊"
                ),
                parse_mode="MarkdownV2",
                reply_markup=main_keyboard(),
            )
        except Exception:
            # اگر کاربر پیام خصوصی ربات رو بلاک داشته باشه
            logger.info(f"نتونستم به {name} پیام خصوصی بدم (احتمالاً بلاک)")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔘  Callback دکمه‌های اینلاین
# ═══════════════════════════════════════════════════════════════════════════════
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    async def show_news(fetch_coro, title, emoji):
        await query.edit_message_text("⏳ در حال دریافت اخبار...")
        articles = await fetch_coro
        text = build_news_text(articles, title, emoji)
        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]
            ]),
        )

    if data == "news_laliga":
        await show_news(
            fetch_news("La Liga football Spain", 5),
            "اخبار لالیگا", "⚽"
        )
    elif data == "news_premier":
        await show_news(
            fetch_news("Premier League England football", 5),
            "اخبار لیگ برتر انگلیس", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
        )
    elif data == "news_politics":
        await show_news(
            fetch_headlines("general", 5),
            "اخبار سیاسی جهان", "🌍"
        )
    elif data == "news_all":
        await query.edit_message_text("⏳ در حال دریافت اخبار...")
        pol = await fetch_headlines("general", 3)
        foot = await fetch_news("La Liga OR Premier League football", 3)
        full = (
            build_news_text(pol, "اخبار سیاسی جهان", "🌍")
            + "\n\n"
            + build_news_text(foot, "اخبار فوتبال", "⚽")
        )
        await query.edit_message_text(
            full,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]
            ]),
        )
    elif data == "prices":
        await query.edit_message_text("⏳ در حال دریافت قیمت‌ها...")
        text = await fetch_prices()
        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]
            ]),
        )
    elif data == "help":
        await query.edit_message_text(
            "📖 *راهنما*\n\n"
            "در پیوی: مستقیم پیام بده\n"
            "در گروه: منشنم کن\n\n"
            "/news — اخبار\n"
            "/prices — قیمت‌ها\n"
            "/clear — پاک کردن حافظه",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]
            ]),
        )
    elif data == "back_main":
        await query.edit_message_text(
            "🏠 منوی اصلی — چی می‌خوای؟",
            reply_markup=main_keyboard(),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀  راه‌اندازی
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # دستورات
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("news",   cmd_news))
    app.add_handler(CommandHandler("prices", cmd_prices))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(CommandHandler("help",   cmd_help))

    # اعضای جدید
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))

    # پیام‌های متنی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # دکمه‌های اینلاین
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ارسال خودکار روزانه ساعت ۰۸:۰۰ صبح
    app.job_queue.run_daily(
        job_daily_news,
        time=dtime(hour=8, minute=0),
        name="daily_news_bundle",
    )

    logger.info("🤖 ربات راه‌اندازی شد! منتظر پیام...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
