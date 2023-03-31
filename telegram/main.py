import os
import json
import asyncio
import traceback
import functions_framework
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters


async def help_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    await update.message.reply_text("Use /issue <asset code> <quantity> to issue your tokens")
    
#bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
# Init the Telegram application
application = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
# define command handler
application.add_handler(CommandHandler("help", help_command_handler))
# define message handler
#dispatcher.add_handler(MessageHandler(filters.text, main_handler))


@functions_framework.http
def webhook(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    try:
        if request.method == "POST":
            update = Update.de_json(request.get_json(force=True), application.bot)
            application.process_update(update)
            return ('', 200)
        else:
            return ('Bad request', 400)
    except Exception as e:
        print('Exception in webhook [%s]' % e)
        traceback.print_exc()
        return ('Exception', 500)
