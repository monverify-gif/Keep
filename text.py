import os
import logging
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters
)

# ---------------- CONFIG ---------------- #

TOKEN = "7701028392:AAFjLuU1_h7qv1jxL9lE8tW4WWD7KJgSuno"

BANNED_WORDS = [
    "scam",
    "fraud",
    "theft",
    "lie",
    "steal",
    "thief",
    "extortion",
    "blackmail",
    "bribery",
    "embezzlement",
    "counterfeit",
    "fake",
    "criminal",
    "cheat",
    "money-laundering"
]

WARNING_LIMIT = 5

# ---------------------------------------- #

user_warnings = {}

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# Auto delete messages
async def delete_later(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Auto delete failed: {e}")


# When bot becomes admin
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    result = update.my_chat_member
    if not result:
        return

    new_status = result.new_chat_member.status

    if new_status in ["administrator", "creator"]:
        try:
            await context.bot.send_message(
                chat_id=result.chat.id,
                text="🛡 Moderation bot active\nScanning messages..."
            )
        except Exception as e:
            logger.error(f"Startup message failed: {e}")


# Scan incoming messages
async def scan_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.message

    if not message or not message.text:
        return

    text = message.text.lower()
    user = message.from_user
    user_id = user.id
    username = user.first_name
    chat_id = message.chat.id

    for word in BANNED_WORDS:

        if word in text:

            # Delete suspicious message
            asyncio.create_task(delete_later(message, 2))

            # Record warning
            user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
            warnings = user_warnings[user_id]

            logger.info(f"{username} warned ({warnings}/{WARNING_LIMIT})")

            try:
                warning_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {username}, suspicious content detected.\n"
                         f"Warning {warnings}/{WARNING_LIMIT}"
                )

                asyncio.create_task(delete_later(warning_msg, 10))

            except Exception as e:
                logger.error(f"Warning message failed: {e}")

            # Permanent ban if warning limit reached
            if warnings >= WARNING_LIMIT:

                try:
                    await context.bot.ban_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        revoke_messages=True
                    )

                    removal_msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚫 {username} permanently banned after {WARNING_LIMIT} warnings."
                    )

                    asyncio.create_task(delete_later(removal_msg, 10))

                    logger.info(f"{username} permanently banned.")

                except Exception as e:
                    logger.error(f"Failed to ban user: {e}")

            break


# Main function
def main():

    os.system('cls' if os.name == 'nt' else 'clear')

    print("🛡 Moderation Bot Running...")
    print("Waiting for admin privileges...")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_handler(
        ChatMemberHandler(admin_status, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, scan_message)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
