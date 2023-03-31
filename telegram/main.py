import os
import json
import asyncio
import traceback
import functions_framework
import telegram
from telegram.ext import Dispatcher, CommandHandler, MessageHandler

bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])
dispatcher = Dispatcher(bot, None, use_context=True)

# define command handler
dispatcher.add_handler(CommandHandler("help", help_command_handler))
# define message handler
#dispatcher.add_handler(MessageHandler(Filters.text, main_handler))

async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    await update.message.reply_text("Use /issue <asset code> <quantity> to issue your tokens")

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
            update = telegram.Update.de_json(request.get_json(force=True), bot)
            dispatcher.process_update(update)
            return ('', 200)
        else:
            return ('Bad request', 400)
    except Exception as e:
        print('Exception in webhook [%s]' % e)
        traceback.print_exc()
        return ('Exception', 500)
