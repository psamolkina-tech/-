"""
Telegram Bot for Video Rewards Mini App
Handles bot commands and channel subscription verification
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatMemberHandler
)
import httpx

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user

    # Check for referral code
    referral_code = None
    if context.args:
        referral_code = context.args[0]

    # Build webapp URL with referral
    webapp_url = WEBAPP_URL
    if referral_code:
        webapp_url = f"{WEBAPP_URL}?startapp={referral_code}"

    # Create keyboard with Mini App button
    keyboard = [
        [InlineKeyboardButton(
            "🎬 Смотреть видео и получать звезды",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton(
            "📢 Подписаться на канал",
            url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"
        )],
        [InlineKeyboardButton(
            "👥 Пригласить друзей",
            callback_data="invite_friends"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = f"""
👋 Привет, {user.first_name}!

🎬 **Video Rewards** - смотри видео и получай бонусы!

⭐ **Как заработать звезды:**
• Смотри видео - +1 звезда
• Подпишись на канал - +1 звезда
• Пригласи друга - +1 звезда

🎁 **За 3 звезды получи скидку 60 000 ₽!**

Нажми кнопку ниже, чтобы начать 👇
"""

    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """
📖 **Помощь**

**Как получить скидку 60 000 ₽?**

1️⃣ Смотри видео в приложении (минимум 80%)
2️⃣ Подпишись на наш канал
3️⃣ Пригласи друзей по реферальной ссылке

За каждое действие ты получаешь ⭐ звезду.
Собери 3 звезды и получи скидку!

**Команды:**
/start - Открыть приложение
/help - Эта справка
/mystars - Узнать баланс звезд
/invite - Получить реферальную ссылку

По вопросам: @support_username
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def mystars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mystars command - show user's star balance"""
    user = update.effective_user

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/user/{user.id}")

            if response.status_code == 200:
                data = response.json()
                stars = data.get('stars', 0)
                discount_available = data.get('discount_available', False)

                if discount_available:
                    message = f"""
⭐ У тебя {stars} звезд(ы)!

🎉 **Поздравляем!** Ты можешь получить скидку 60 000 ₽!
Открой приложение и нажми "Получить скидку".
"""
                else:
                    remaining = 3 - stars
                    message = f"""
⭐ У тебя {stars} звезд(ы)!

{'🎯 Осталось собрать: ' + str(remaining) + ' звезд(ы) до скидки 60 000 ₽' if remaining > 0 else ''}
"""

                keyboard = [[InlineKeyboardButton(
                    "🎬 Открыть приложение",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "Ты еще не начал(а). Нажми /start чтобы начать!"
                )

    except Exception as e:
        logger.error(f"Error fetching stars: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуй позже."
        )


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /invite command - get referral link"""
    user = update.effective_user

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/api/referral/stats",
                params={"telegram_id": user.id}
            )

            if response.status_code == 200:
                data = response.json()
                referral_code = data.get('referral_code', '')
                referral_count = data.get('referral_count', 0)

                # Generate bot referral link
                bot_username = (await context.bot.get_me()).username
                referral_link = f"https://t.me/{bot_username}?start={referral_code}"

                message = f"""
👥 **Реферальная программа**

📊 Приглашено друзей: {referral_count}
⭐ Заработано звезд: {referral_count}

🔗 **Твоя ссылка:**
`{referral_link}`

Поделись ссылкой с друзьями и получай звезды!
"""

                keyboard = [
                    [InlineKeyboardButton(
                        "📤 Поделиться",
                        url=f"https://t.me/share/url?url={referral_link}&text=Смотри видео и получи скидку 60 000 ₽!"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "Сначала нажми /start чтобы зарегистрироваться!"
                )

    except Exception as e:
        logger.error(f"Error fetching referral stats: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуй позже."
        )


async def invite_friends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle invite friends button callback"""
    query = update.callback_query
    await query.answer()

    # Redirect to invite command logic
    user = query.from_user

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/api/referral/stats",
                params={"telegram_id": user.id}
            )

            if response.status_code == 200:
                data = response.json()
                referral_code = data.get('referral_code', '')
                referral_count = data.get('referral_count', 0)

                bot_username = (await context.bot.get_me()).username
                referral_link = f"https://t.me/{bot_username}?start={referral_code}"

                message = f"""
👥 **Пригласи друзей**

📊 Уже приглашено: {referral_count}

🔗 **Твоя ссылка:**
`{referral_link}`

За каждого друга ты получишь ⭐ звезду!
"""

                keyboard = [
                    [InlineKeyboardButton(
                        "📤 Поделиться ссылкой",
                        url=f"https://t.me/share/url?url={referral_link}&text=Смотри видео и получи скидку 60 000 ₽!"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

    except Exception as e:
        logger.error(f"Error in invite callback: {e}")


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Check if user is subscribed to the channel"""
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False


async def verify_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify channel subscription and award star"""
    user = update.effective_user

    is_subscribed = await check_subscription(update, context, user.id)

    if is_subscribed:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/api/subscribe/check",
                    params={"telegram_id": user.id}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get('stars_earned', 0) > 0:
                        await update.message.reply_text(
                            "✅ Подписка подтверждена! Ты получил(а) ⭐ звезду!"
                        )
                    else:
                        await update.message.reply_text(
                            "✅ Ты уже получил(а) награду за подписку!"
                        )
        except Exception as e:
            logger.error(f"Error verifying subscription: {e}")
    else:
        keyboard = [[InlineKeyboardButton(
            "📢 Подписаться на канал",
            url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "❌ Ты еще не подписан(а) на канал. Подпишись и попробуй снова!",
            reply_markup=reply_markup
        )


def main() -> None:
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mystars", mystars))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("checksub", verify_subscription))
    application.add_handler(CallbackQueryHandler(invite_friends_callback, pattern="^invite_friends$"))

    # Start polling
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
