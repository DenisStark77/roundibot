import os
import json
import traceback
import functions_framework
from telegram import Bot, Update, Updater
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

# /help command wrapper 
def help_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    print('DEBUG!!! Sending reply')
    update.message.reply_text("Use /issue <asset code> <quantity> to issue your tokens")

# Init the Telegram application
if os.getenv('BOT_ENV') == 'TEST':
    # Create the Updater and pass it your bot's token.
    updater = Updater(os.getenv('TELEGRAM_TOKEN'))

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
else:
    # Create the Bot and pass it your bot's token.
    bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))

    # Create the dispatcher to register handlers
    dispatcher = Dispatcher(bot, None, use_context=True)

# define command handler
print('DEBUG!!! Adding handler')
dispatcher.add_handler(CommandHandler(["start", "help"], help_command_handler))
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
            update = Update.de_json(request.get_json(force=True), bot)
            print('DEBUG!!! Updating process')
            dispatcher.process_update(update)
            return ('', 200)
        else:
            return ('Bad request', 400)
    except Exception as e:
        print('Exception in webhook [%s]' % e)
        traceback.print_exc()
        return ('Exception', 500)
    
    
def main():
    """Run the bot."""
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
