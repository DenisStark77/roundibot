import os
import traceback
import functions_framework
import telegram

bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

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
            async with bot as bot:
                await bot.sendMessage(update.message.chat.id, text='Hello, hello!') # update.message.text
            return ('', 204)
        else:
            return ('Bad request', 400)
    except Exception as e:
        print('Exception in webhook [%s]' % e)
        traceback.print_exc()
        return ('Exception', 400)
