import os
import json
import traceback
import functions_framework
from telegram import Bot, Update
from telegram.ext import Dispatcher, Updater, CommandHandler, MessageHandler, filters

from google.cloud import datastore
client = datastore.Client()

# /start command wrapper 
def start_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    print('DEBUG!!! Sending reply')
    update.message.reply_text("To start use /list command to see available tokens")

# /help command wrapper 
def help_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Query current user and see what he has already
    #TODO: If nothing recommend the /list command
    #TODO: If has trusted assets with zero balances recommend to earn
    #TODO: If has trusted assets with balances recommend to pay
    #TODO: If has trusted assets with balances and payment history recommend to create orders
    #TODO: If has trusted assets and orders recommend to issue own tokens
    #TODO: If has own tokens with no orders for it recommend to create orders

    update.message.reply_text("Use /list command to see available tokens")

# /issue command wrapper 
def issue_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Check if asset code is not exist
    #TODO: If exist and belong to current user issue extra tokens
    #TODO: If not exist create and issue tokens
    
    update.message.reply_text("Ask your counterparty to use /trust <asset> command, so you'll be able to transfer tokens to them.")

# /list command wrapper 
def list_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: send list of available tokens
    
    update.message.reply_text("Use /trust <asset code> or /trust <asset code> <quantity> to trust the token")

# /trust command wrapper 
def trust_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: set trust to the asset
    #TODO: if user has non zero balances check paths to the new asset and show how to order it
    
    update.message.reply_text("Use /order <amount> <buying asset> <amount> <selling assed> to order these tokens")

# /send command wrapper 
def send_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Send given number of the asset to specified user via path payment
    
    update.message.reply_text("Use /order <amount> <buying asset> <amount> <selling assed> to exchange tokens to another token")

# /order command wrapper 
def order_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Create the order
    update.message.reply_text("Use /book to see list of your orders")

# /pay command wrapper 
def pay_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Pay given amount to the issuer of the specified token
    #TODO: Check the situation with with specified token
    #TODO: If user has no trust for this asset and regularly paying with it - offer to trust this asset
    #TODO: If user has small or zero balance for asset and regularly paying with it - offer to create an order

    update.message.reply_text("Use /order <amount> <asset> <amount> <selling asset>") 

# /balance command wrapper 
def balance_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Show balances of the assount
    #TODO: If user has own asset check the paths to each asset from the key asset and show the prices to order
    #TODO: If user do not have trusted assets offer to use /list command to add some assets
    #TODO: If user have several non zero balances and do not have own asset, offer to /issue own token
    
    update.message.reply_text("Use /book command to see order book for all your assets")

# /book command wrapper 
def book_command_handler(update, context):
    """Sends explanation on how to use the bot."""
    #TODO: Show all orders in order book for given user
    #TODO: If no trust for asset offer to use /trust command
    #TODO: If all balances is zero suggest to earn tokens (not possible to create orders w/o balance)
    
    update.message.reply_text("Use /order <amount> <buying asset> <amount> <selling assed> to order other tokens")

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
dispatcher.add_handler(CommandHandler("start", start_command_handler))
dispatcher.add_handler(CommandHandler(["he", "help"], help_command_handler))
dispatcher.add_handler(CommandHandler(["is", "issue"], issue_command_handler))
dispatcher.add_handler(CommandHandler(["li", "list"], list_command_handler))
dispatcher.add_handler(CommandHandler(["tr", "trust"], trust_command_handler))
dispatcher.add_handler(CommandHandler(["se", "send"], send_command_handler))
dispatcher.add_handler(CommandHandler(["or", "order"], order_command_handler))
dispatcher.add_handler(CommandHandler(["pa", "pay"], pay_command_handler))
dispatcher.add_handler(CommandHandler(["ba","balance"], balance_command_handler))
dispatcher.add_handler(CommandHandler(["bo","book"], book_command_handler))
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
