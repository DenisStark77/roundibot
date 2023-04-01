import os
import json
import asyncio
import traceback
import functions_framework
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# /help command wrapper 
async def help_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    print('DEBUG!!! Sending reply')
    await update.message.reply_text("Use /issue <asset code> <quantity> to issue your tokens")

# Run async function from webhook
async def init():
    # Initialize application
    print('DEBUG!!! Initializing')
    await application.initialize()
    if not application.running:
        print('DEBUG!!! Starting')
        await application.start()
    else:    
        await application.stop()
        await application.start()
        print('DEBUG!!! Application already running')
    print('DEBUG!!! Started', application.running)


# Init the Telegram application
application = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).updater(None).build()
#application = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
# define command handler
print('DEBUG!!! Adding handler')
application.add_handler(CommandHandler(["start", "help"], help_command_handler))
# define message handler
#dispatcher.add_handler(MessageHandler(filters.text, main_handler))
#asyncio.run(init())


# Run async function from webhook
async def process_update(update):
    await init()
    print('DEBUG!!! update_queue BEFORE', application.update_queue.qsize())
    await application.update_queue.put(update)
    print('DEBUG!!! update_queue AFTER', application.update_queue.qsize())


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
            print('DEBUG!!! Updating process', 'Application running:', application.running, application.update_queue.qsize())
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(process_update(update))
            except RuntimeError as r:
                print('DEBUG!!! No running loop')
                asyncio.run(process_update(update))
            #application.update_queue.put_nowait(update)
            #loop = asyncio.new_event_loop()
            #asyncio.set_event_loop(loop)
            #loop.run_until_complete(process_update(update))
            print('DEBUG!!! update_queue', application.update_queue.qsize())
            return ('', 200)
        else:
            return ('Bad request', 400)
    except Exception as e:
        print('Exception in webhook [%s]' % e)
        traceback.print_exc()
        return ('Exception', 500)
