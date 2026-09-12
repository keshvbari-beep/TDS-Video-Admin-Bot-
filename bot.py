import os
import io
import logging
from PIL import Image

from supabase import create_client, Client

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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SUPPORT_URL = "https://t.me/RajanChauhan_club"
SEARCH_BOT_URL = "https://t.me/TSB_Video_Search_Bot"


# =========================================================
# CHANNELS
# =========================================================

CHANNELS = {
    "1": -1004338671388,
    "2": -1004490954138,
    "3": -1003963263624,
    "4": -1003472229143,
}


# =========================================================
# THUMBNAIL - 4:5
# =========================================================

THUMB_WIDTH = 1280
THUMB_HEIGHT = 1600


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# SUPABASE
# =========================================================

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )


# =========================================================
# CONVERSATION STATES
# =========================================================

CHANNEL, CODE, PHOTO, TITLE, DESCRIPTION, LINK, PREVIEW = range(7)


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(update: Update) -> bool:

    user = update.effective_user

    if not user:
        return False

    return user.id == ADMIN_USER_ID


# =========================================================
# DENIED
# =========================================================

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

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

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
# CREATE POST
# =========================================================

async def create_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton(
                "CHANNEL 1",
                callback_data="channel_1",
            ),
            InlineKeyboardButton(
                "CHANNEL 2",
                callback_data="channel_2",
            ),
        ],
        [
            InlineKeyboardButton(
                "CHANNEL 3",
                callback_data="channel_3",
            ),
            InlineKeyboardButton(
                "CHANNEL 4",
                callback_data="channel_4",
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ CANCEL",
                callback_data="cancel",
            ),
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

async def select_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    channel_number = query.data.replace(
        "channel_",
        "",
    )

    context.user_data["channel"] = channel_number

    await query.edit_message_text(
        f"✅ Channel {channel_number} Selected\n\n"
        "🔢 अब Post का **Code** भेजो।\n\n"
        "Example: `1P-1001`",
        parse_mode="Markdown",
    )

    return CODE


# =========================================================
# RECEIVE CODE
# =========================================================

async def receive_code(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    if not update.message or not update.message.text:
        return CODE

    code = update.message.text.strip()

    if not code:

        await update.message.reply_text(
            "⚠️ Code खाली नहीं हो सकता।\n\n"
            "Example: `1P-1001`",
            parse_mode="Markdown",
        )

        return CODE

    if len(code) < 3:

        await update.message.reply_text(
            "⚠️ Code सही डालो।\n\n"
            "Example: `1P-1001`",
        )

        return CODE

    context.user_data["code"] = code

    await update.message.reply_text(
        "✅ Code Saved\n\n"
        "🖼️ अब अपनी Thumbnail / Photo भेजो।\n\n"
        "Photo automatically 4:5 format में crop होगी।"
    )

    return PHOTO


# =========================================================
# RECEIVE PHOTO
# =========================================================

async def receive_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    if not update.message or not update.message.photo:

        await update.message.reply_text(
            "⚠️ कृपया Photo भेजो।"
        )

        return PHOTO

    photo = update.message.photo[-1]

    telegram_file = await context.bot.get_file(
        photo.file_id
    )

    image_bytes = io.BytesIO()

    await telegram_file.download_to_memory(
        image_bytes
    )

    image_bytes.seek(0)

    try:

        image = Image.open(
            image_bytes
        ).convert("RGB")

        # =================================================
        # CROP TO 4:5
        # =================================================

        target_ratio = (
            THUMB_WIDTH /
            THUMB_HEIGHT
        )

        current_ratio = (
            image.width /
            image.height
        )

        if current_ratio > target_ratio:

            new_width = int(
                image.height *
                target_ratio
            )

            left = (
                image.width -
                new_width
            ) // 2

            image = image.crop(
                (
                    left,
                    0,
                    left + new_width,
                    image.height,
                )
            )

        else:

            new_height = int(
                image.width /
                target_ratio
            )

            top = (
                image.height -
                new_height
            ) // 2

            image = image.crop(
                (
                    0,
                    top,
                    image.width,
                    top + new_height,
                )
            )

        # =================================================
        # RESIZE
        # =================================================

        image = image.resize(
            (
                THUMB_WIDTH,
                THUMB_HEIGHT,
            ),
            Image.Resampling.LANCZOS,
        )

        output = io.BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=90,
        )

        output.seek(0)

        context.user_data["photo"] = (
            output.getvalue()
        )

    except Exception as e:

        logger.exception(
            "Image processing error"
        )

        await update.message.reply_text(
            "❌ Photo process नहीं हो पाई।\n"
            "दूसरी photo try करो।"
        )

        return PHOTO

    await update.message.reply_text(
        "✅ Thumbnail तैयार हो गई।\n\n"
        "✍️ अब अपना **Title** भेजो।"
    )

    return TITLE


# =========================================================
# RECEIVE TITLE
# =========================================================

async def receive_title(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    if not update.message or not update.message.text:
        return TITLE

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
# RECEIVE DESCRIPTION
# =========================================================

async def receive_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    if not update.message or not update.message.text:
        return DESCRIPTION

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
# RECEIVE LINK
# =========================================================

async def receive_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    if not update.message or not update.message.text:
        return LINK

    link = update.message.text.strip()

    if not (
        link.startswith("http://")
        or link.startswith("https://")
    ):

        await update.message.reply_text(
            "⚠️ सही link भेजो जो "
            "http:// या https:// से शुरू हो।"
        )

        return LINK

    context.user_data["link"] = link

    return await show_preview(
        update,
        context,
    )


# =========================================================
# SHOW PREVIEW
# =========================================================

async def show_preview(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    data = context.user_data

    channel = data["channel"]
    code = data["code"]
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

    await update.message.reply_photo(
        photo=io.BytesIO(data["photo"]),
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text(
        f"👀 Preview तैयार है।\n\n"
        f"📢 Channel: {channel}\n"
        f"🔢 Code: {code}\n"
        f"🖼️ Thumbnail: 4:5\n\n"
        f"सब सही है तो 🚀 SEND POST दबाओ।"
    )

    return PREVIEW


# =========================================================
# SEND POST + SUPABASE
# =========================================================

async def send_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    if not is_admin(update):
        await denied(update)
        return ConversationHandler.END

    data = context.user_data

    try:

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

        # =================================================
        # SEND POST TO CHANNEL
        # =================================================

        sent_message = await context.bot.send_photo(
            chat_id=channel_id,
            photo=io.BytesIO(data["photo"]),
            caption=caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        message_id = sent_message.message_id

        logger.info(
            "Telegram channel post sent. Message ID: %s",
            message_id,
        )

        # =================================================
        # SUPABASE CHECK
        # =================================================

        if not supabase:

            raise RuntimeError(
                "Supabase configuration missing."
            )

        # =================================================
        # DATABASE ROW
        # =================================================

        row = {
            "code": data["code"],
            "channel_id": str(channel_id),
            "message_id": str(message_id),
            "name": data["title"],
            "description": data["description"],
            "photo": (
                sent_message.photo[-1].file_id
                if sent_message.photo
                else None
            ),
        }

        # =================================================
        # INSERT
        # =================================================

        result = (
            supabase
            .table("videos")
            .insert(row)
            .execute()
        )

        logger.info(
            "Supabase save successful: %s",
            result,
        )

        # =================================================
        # SUCCESS
        # =================================================

        success_text = (
            "✅ POST SUCCESSFULLY SENT!\n\n"
            f"📢 Channel {channel_number}\n"
            f"🔢 Code: {data['code']}\n"
            "🖼️ Thumbnail 4:5 ✓\n"
            "📝 Title ✓\n"
            "📄 Description ✓\n"
            "🔗 GET LINK ✓\n"
            "💾 Database Save ✓\n"
            f"🆔 Message ID: {message_id}"
        )

        # IMPORTANT:
        # SEND POST button photo message पर है।
        # इसलिए edit_message_text() नहीं।
        # edit_caption() इस्तेमाल होगा।

        if query.message:

            await query.message.edit_caption(
                caption=success_text,
                reply_markup=None,
            )

    except Exception as e:

        logger.exception(
            "Send/Database error"
        )

        error_text = (
            "❌ Post process में error आया।\n\n"
            f"Error: {str(e)[:500]}"
        )

        # =================================================
        # ERROR MESSAGE
        # =================================================

        try:

            if query.message:

                await query.message.edit_caption(
                    caption=error_text,
                    reply_markup=None,
                )

        except Exception as edit_error:

            logger.error(
                "Could not edit preview caption: %s",
                edit_error,
            )

            if query.message:

                await query.message.reply_text(
                    error_text
                )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# CANCEL
# =========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.callback_query:

        query = update.callback_query

        await query.answer()

        try:

            await query.message.edit_caption(
                caption="❌ Post creation cancelled.",
                reply_markup=None,
            )

        except Exception:

            await query.message.reply_text(
                "❌ Post creation cancelled."
            )

    elif update.message:

        await update.message.reply_text(
            "❌ Post creation cancelled."
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# MY ID
# =========================================================

async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user:
        return

    await update.message.reply_text(
        f"🆔 आपका Telegram User ID:\n\n"
        f"`{user.id}`",
        parse_mode="Markdown",
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # =====================================================
    # CHECK SETTINGS
    # =====================================================

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN GitHub Secret में नहीं मिला।"
        )

    if ADMIN_USER_ID == 0:

        raise RuntimeError(
            "ADMIN_USER_ID GitHub Secret में नहीं मिला।"
        )

    if not SUPABASE_URL:

        raise RuntimeError(
            "SUPABASE_URL GitHub Secret में नहीं मिला।"
        )

    if not SUPABASE_KEY:

        raise RuntimeError(
            "SUPABASE_KEY GitHub Secret में नहीं मिला।"
        )

    # =====================================================
    # APPLICATION
    # =====================================================

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # CONVERSATION
    # =====================================================

    conversation = ConversationHandler(

        entry_points=[
            CallbackQueryHandler(
                create_post,
                pattern="^create$",
            )
        ],

        states={

            # ---------------------------------------------
            # CHANNEL
            # ---------------------------------------------

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

            # ---------------------------------------------
            # CODE
            # ---------------------------------------------

            CODE: [

                MessageHandler(
                    filters.TEXT &
                    ~filters.COMMAND,
                    receive_code,
                ),
            ],

            # ---------------------------------------------
            # PHOTO
            # ---------------------------------------------

            PHOTO: [

                MessageHandler(
                    filters.PHOTO,
                    receive_photo,
                ),
            ],

            # ---------------------------------------------
            # TITLE
            # ---------------------------------------------

            TITLE: [

                MessageHandler(
                    filters.TEXT &
                    ~filters.COMMAND,
                    receive_title,
                ),
            ],

            # ---------------------------------------------
            # DESCRIPTION
            # ---------------------------------------------

            DESCRIPTION: [

                MessageHandler(
                    filters.TEXT &
                    ~filters.COMMAND,
                    receive_description,
                ),
            ],

            # ---------------------------------------------
            # LINK
            # ---------------------------------------------

            LINK: [

                MessageHandler(
                    filters.TEXT &
                    ~filters.COMMAND,
                    receive_link,
                ),
            ],

            # ---------------------------------------------
            # PREVIEW
            # ---------------------------------------------

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
            CommandHandler(
                "cancel",
                cancel,
            ),
        ],

        allow_reentry=True,
    )

    # =====================================================
    # COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "id",
            my_id,
        )
    )

    application.add_handler(
        conversation
    )

    # =====================================================
    # RUN
    # =====================================================

    print(
        "TDS Video Admin Bot is running..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# START PROGRAM
# =========================================================

if __name__ == "__main__":
    main()
