"""
بات اصلی RPG تلگرام
"""
import os
import logging
from datetime import time
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from data.database import init_db
from handlers import shop, duel, stealth, admin, claim
from utils.scheduler import daily_leaderboard, daily_points_reward

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from data import database as db
    user = update.effective_user
    db.create_user(user.id, user.username, user.first_name)

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"⚔️ *سلام {user.first_name}! به دنیای RPG خوش اومدی!*\n\n"
            f"🏪 /shop — فروشگاه (خرید آیتم)\n"
            f"🎁 /claim — دریافت امتیاز رایگان (هر ۸ ساعت)\n"
            f"🗡️ /stealth — حمله مخفیانه\n"
            f"📊 /profile — پروفایل من\n"
            f"🏆 /top — لیدربورد\n\n"
            f"*در گروه:*\n"
            f"⚔️ /duel — درخواست دوئل (reply روی پیام کسی)\n"
            f"/use [item_id] — استفاده از آیتم در دوئل\n"
            f"/status — وضعیت دوئل فعال\n\n"
            f"💡 اول /claim بزن و امتیاز رایگان بگیر، بعد از /shop آیتم بخر!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"⚔️ {user.first_name} عضو بازی شد!\n"
            f"برای خرید آیتم به پیوی بات برو: @{context.bot.username}"
        )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from data import database as db
    from utils.combat import calc_user_stats
    user = update.effective_user
    db.create_user(user.id, user.username, user.first_name)
    u = db.get_user(user.id)
    max_hp, max_mana = calc_user_stats(user.id)
    rings = db.get_rings(user.id)

    from data.items import get_item
    r1 = get_item(rings["ring1"])
    r2 = get_item(rings["ring2"])

    await update.message.reply_text(
        f"👤 *{u['first_name']}*\n\n"
        f"💎 امتیاز: *{u['points']}*\n"
        f"❤️ HP: {u['hp']}/{max_hp}\n"
        f"💧 مانا: {u['mana']}/{max_mana}\n"
        f"⚔️ برد: *{u['wins']}* | 💀 باخت: *{u['losses']}*\n"
        f"🗡️ حمله مخفیانه: *{u['stealth_kills']}*\n\n"
        f"💍 انگشتری ۱: {r1['name'] if r1 else '—'}\n"
        f"💍 انگشتری ۲: {r2['name'] if r2 else '—'}",
        parse_mode="Markdown"
    )


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from data import database as db
    lb = db.get_leaderboard(10)
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *برترین مبارزان:*\n"]
    for i, u in enumerate(lb):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {u['first_name']} — 💎{u['points']} | ⚔️{u['wins']}W")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر پیام‌های متنی در پیوی"""
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    # ادمین
    if admin.is_admin(user_id) and context.user_data.get("admin_action"):
        await admin.admin_message_handler(update, context)
        return

    # حمله مخفیانه
    if context.user_data.get("stealth_state") == "awaiting_target":
        await stealth.stealth_receive_target(update, context)
        return


async def set_commands(app):
    commands = [
        BotCommand("start", "شروع بازی"),
        BotCommand("shop", "فروشگاه آیتم‌ها"),
        BotCommand("claim", "دریافت امتیاز رایگان (هر ۸ ساعت)"),
        BotCommand("profile", "پروفایل من"),
        BotCommand("top", "لیدربورد"),
        BotCommand("stealth", "حمله مخفیانه"),
        BotCommand("duel", "درخواست دوئل در گروه"),
        BotCommand("use", "استفاده از آیتم در دوئل"),
        BotCommand("status", "وضعیت دوئل"),
        BotCommand("cancel", "لغو عملیات"),
        BotCommand("admin", "پنل ادمین"),
    ]
    await app.bot.set_my_commands(commands)


def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # ─── Command handlers ───
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop.shop_start))
    app.add_handler(CommandHandler("claim", claim.claim_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("stealth", stealth.stealth_start))
    app.add_handler(CommandHandler("cancel", stealth.cancel_command))
    app.add_handler(CommandHandler("duel", duel.duel_command))
    app.add_handler(CommandHandler("use", duel.use_item_command))
    app.add_handler(CommandHandler("status", duel.duel_status))
    app.add_handler(CommandHandler("admin", admin.admin_panel))

    # ─── Callback handlers ───
    app.add_handler(CallbackQueryHandler(shop.shop_category, pattern="^shop_cat_"))
    app.add_handler(CallbackQueryHandler(shop.shop_item_detail, pattern="^shop_item_"))
    app.add_handler(CallbackQueryHandler(shop.buy_item, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(shop.equip_ring, pattern="^equip_ring_"))
    app.add_handler(CallbackQueryHandler(shop.my_inventory, pattern="^my_inventory$"))
    app.add_handler(CallbackQueryHandler(shop.my_profile, pattern="^my_profile$"))
    app.add_handler(CallbackQueryHandler(shop.shop_back, pattern="^shop_back$"))
    app.add_handler(CallbackQueryHandler(claim.claim_status_callback, pattern="^claim_status$"))

    app.add_handler(CallbackQueryHandler(duel.accept_duel, pattern="^accept_duel_"))
    app.add_handler(CallbackQueryHandler(duel.reject_duel, pattern="^reject_duel_"))

    app.add_handler(CallbackQueryHandler(stealth.stealth_confirm, pattern="^confirm_stealth_"))
    app.add_handler(CallbackQueryHandler(stealth.stealth_cancel, pattern="^cancel_stealth$"))

    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern="^admin_"))

    # ─── Message handler ───
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_private_message
    ))

    # ─── Scheduler ───
    job_queue = app.job_queue
    # لیدربورد هر روز ساعت ۸ صبح UTC+3:30 یعنی 04:30 UTC
    job_queue.run_daily(daily_leaderboard, time=time(4, 30), name="daily_leaderboard")
    # جایزه روزانه ساعت ۶ صبح ایران = 02:30 UTC
    job_queue.run_daily(daily_points_reward, time=time(2, 30), name="daily_points")

    # راه‌اندازی
    app.post_init = set_commands
    logger.info("🤖 بات در حال اجرا...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
