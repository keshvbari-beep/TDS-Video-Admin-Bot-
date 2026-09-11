import os
import io
import logging
from PIL import Image

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

SUPPORT_URL = "https://t.me/RajanChauhan_club"
SEARCH_BOT_URL = "https://t.me/TSB_Video_Search_Bot"

CHANNELS = {
    "1": -1004338671388,
    "2": -1004490954138,
    "3": -1003963263624,
    "4": -1003472229143,
}

# Fixed thumbnail size
THUMB_WIDTH = 1280
THUMB_HEIGHT = 720

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# STATES
# =========================================================

CHANNEL, PHOTO, TITLE, DESCRIPTION, LINK, PREVIEW = range(6)


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(update: Update) -> bool:
    user = update.effective_user

    if not user:
        return False

    return user.id == ADMIN_USER_ID


async def denied(update: Update):
    if update.callback_query:
        await update.callback_query.answer(
            "⛔ यह bot सिर्फ admin के लिए है।",
            show_alert=True,
        )
    elif update.message:
        await update.message.reply_text(
            "⛔ यह bot सिर्फ admin के लिए है।"
        )


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    context.user_data.clear()

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ CREATE POST",
                callback_data="create",
            )
        ]
    ]

    await update.message.reply_text(
        "👋 Welcome to TDS Video Admin\n\n"
        "यहाँ से अपना Channel Post बनाओ।",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return ConversationHandler.END


# =========================================================
# CREATE BUTTON
# =========================================================

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("CHANNEL 1", callback_data="channel_1"),
            InlineKeyboardButton("CHANNEL 2", callback_data="channel_2"),
        ],
        [
            InlineKeyboardButton("CHANNEL 3", callback_data="channel_3"),
            InlineKeyboardButton("CHANNEL 4", callback_data="channel_4"),
        ],
        [
            InlineKeyboardButton("❌ CANCEL", callback_data="cancel"),
        ],
    ]

    await query.edit_message_text(
        "📢 किस Channel में Post करनी है?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CHANNEL


# =========================================================
# CHANNEL SELECT
# =========================================================

async def select_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    channel_number = query.data.replace("channel_", "")

    context.user_data["channel"] = channel_number

    await query.edit_message_text(
        f"✅ Channel {channel_number} Selected\n\n"
        "🖼️ अब अपनी Thumbnail / Photo भेजो।\n\n"
        "Photo automatically 16:9 format में crop होगी।"
    )

    return PHOTO


# =========================================================
# PHOTO
# =========================================================

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ कृपया Photo भेजो।"
        )
        return PHOTO

    photo = update.message.photo[-1]

    telegram_file = await context.bot.get_file(photo.file_id)

    image_bytes = io.BytesIO()
    await telegram_file.download_to_memory(image_bytes)

    image_bytes.seek(0)

    try:

        image = Image.open(image_bytes).convert("RGB")

        # 16:9 crop
        target_ratio = THUMB_WIDTH / THUMB_HEIGHT
        current_ratio = image.width / image.height

        if current_ratio > target_ratio:
            new_width = int(image.height * target_ratio)

            left = (image.width - new_width) // 2

            image = image.crop(
                (
                    left,
                    0,
                    left + new_width,
                    image.height,
                )
            )

        else:
            new_height = int(image.width / target_ratio)

            top = (image.height - new_height) // 2

            image = image.crop(
                (
                    0,
                    top,
                    image.width,
                    top + new_height,
                )
            )

        image = image.resize(
            (THUMB_WIDTH, THUMB_HEIGHT),
            Image.Resampling.LANCZOS,
        )

        output = io.BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=90,
        )

        output.seek(0)

        context.user_data["photo"] = output.getvalue()

    except Exception as e:

        logger.error("Image processing error: %s", e)

        await update.message.reply_text(
            "❌ Photo process नहीं हो पाई। दूसरी photo try करो।"
        )

        return PHOTO

    await update.message.reply_text(
        "✅ Thumbnail तैयार हो गई।\n\n"
        "✍️ अब अपना **Title** भेजो।"
    )

    return TITLE


# =========================================================
# TITLE
# =========================================================

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    title = update.message.text.strip()

    if not title:
        await update.message.reply_text(
            "⚠️ Title खाली नहीं हो सकता।"
        )
        return TITLE

    context.user_data["title"] = title

    await update.message.reply_text(
        "📝 अब अपना **Description** भेजो।"
    )

    return DESCRIPTION


# =========================================================
# DESCRIPTION
# =========================================================

async def receive_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    description = update.message.text.strip()

    if not description:
        await update.message.reply_text(
            "⚠️ Description खाली नहीं हो सकता।"
        )
        return DESCRIPTION

    context.user_data["description"] = description

    await update.message.reply_text(
        "🔗 अब अपना **TeraBox Link** भेजो।"
    )

    return LINK


# =========================================================
# LINK
# =========================================================

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    link = update.message.text.strip()

    if not (
        link.startswith("http://")
        or link.startswith("https://")
    ):
        await update.message.reply_text(
            "⚠️ सही link भेजो जो http:// या https:// से शुरू हो।"
        )
        return LINK

    context.user_data["link"] = link

    return await show_preview(update, context)


# =========================================================
# PREVIEW
# =========================================================

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = context.user_data

    channel = data["channel"]
    title = data["title"]
    description = data["description"]

    caption = (
        f"🎬 <b>{title}</b>\n\n"
        f"{description}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ GET LINK",
                url=data["link"],
            ),
            InlineKeyboardButton(
                "💬 SUPPORT",
                url=SUPPORT_URL,
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 BACK TO SEARCH",
                url=SEARCH_BOT_URL,
            ),
        ],
        [
            InlineKeyboardButton(
                "🚀 SEND POST",
                callback_data="send_post",
            ),
            InlineKeyboardButton(
                "❌ CANCEL",
                callback_data="cancel",
            ),
        ],
    ]

    # Send preview to admin
    await update.message.reply_photo(
        photo=io.BytesIO(data["photo"]),
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text(
        f"👀 Preview तैयार है।\n\n"
        f"Channel: {channel}\n\n"
        f"सब सही है तो **🚀 SEND POST** दबाओ।",
    )

    return PREVIEW


# =========================================================
# SEND POST
# =========================================================

async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    data = context.user_data

    channel_number = data["channel"]
    channel_id = CHANNELS[channel_number]

    caption = (
        f"🎬 <b>{data['title']}</b>\n\n"
        f"{data['description']}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ GET LINK",
                url=data["link"],
            ),
            InlineKeyboardButton(
                "💬 SUPPORT",
                url=SUPPORT_URL,
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 BACK TO SEARCH",
                url=SEARCH_BOT_URL,
            ),
        ],
    ]

    try:

        await context.bot.send_photo(
            chat_id=channel_id,
            photo=io.BytesIO(data["photo"]),
            caption=caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        await query.edit_message_text(
            f"✅ POST SUCCESSFULLY SENT!\n\n"
            f"📢 Channel {channel_number}\n"
            f"🖼️ Thumbnail ✓\n"
            f"📝 Title ✓\n"
            f"📄 Description ✓\n"
            f"🔗 GET LINK ✓\n"
            f"💬 SUPPORT ✓\n"
            f"🔙 BACK TO SEARCH ✓"
        )

    except Exception as e:

        logger.error("Send error: %s", e)

        await query.edit_message_text(
            "❌ Post भेजने में error आया।\n\n"
            "Check करो कि bot उस channel में Admin है और "
            "Post Messages permission है।"
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# CANCEL
# =========================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:

        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "❌ Post creation cancelled."
        )

    else:

        await update.message.reply_text(
            "❌ Post creation cancelled."
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# UNKNOWN / ID HELPER
# =========================================================

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    await update.message.reply_text(
        f"🆔 आपका Telegram User ID:\n\n"
        f"`{user.id}`",
        parse_mode="Markdown",
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN GitHub Secret में नहीं मिला।"
        )

    if ADMIN_USER_ID == 0:
        raise RuntimeError(
            "ADMIN_USER_ID GitHub Secret में नहीं मिला।"
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    conversation = ConversationHandler(

        entry_points=[
            CallbackQueryHandler(
                create_post,
                pattern="^create$",
            )
        ],

        states={

            CHANNEL: [
                CallbackQueryHandler(
                    select_channel,
                    pattern="^channel_[1-4]$",
                ),
                CallbackQueryHandler(
                    cancel,
                    pattern="^cancel$",
                ),
            ],

            PHOTO: [
                MessageHandler(
                    filters.PHOTO,
                    receive_photo,
                )
            ],

            TITLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_title,
                )
            ],

            DESCRIPTION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_description,
                )
            ],

            LINK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_link,
                )
            ],

            PREVIEW: [
                CallbackQueryHandler(
                    send_post,
                    pattern="^send_post$",
                ),
                CallbackQueryHandler(
                    cancel,
                    pattern="^cancel$",
                ),
            ],
        },

        fallbacks=[
            CommandHandler("cancel", cancel)
        ],

        allow_reentry=True,
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("id", my_id)
    )

    application.add_handler(
        conversation
    )

    print("TDS Video Admin Bot is running...")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
