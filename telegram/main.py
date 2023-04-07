import os
import json
import traceback
import functions_framework
from telegram import Bot, Update
from telegram.ext import Dispatcher, Updater, CommandHandler, MessageHandler, filters
from stellar import st_create_account

# Initialize Firestore client
from google.cloud import firestore
db = firestore.Client()
users = db.collection(u'users')
invites = db.collection(u'invites')

# Telegram bot error handler
def error(update, context):
    """Log Errors caused by Updates."""
    print('Update "%s" caused error "%s"', update, context.error)
    
    
# /start command wrapper 
def start_command_handler(update, context):
    """Initialize wallet by creating Stellar account."""
    print('Message from user: ', update.message.from_user.id, update.message.from_user.username, update.message.chat.id)
    # Check if uid exist in Firestore
    uid = f"{update.message.from_user.id}"
    chat_id = f"{update.message.chat.id}"
    user = users.document(uid).get()
    if user.exists:
        # TODO: Send context dependent hint what to do next
        update.message.reply_text("To start use /list command to see available tokens")
    else:
        # If not in Firestore check if user is invited
        username = update.message.from_user.username.lower()
        invite = invites.document(username).get()
        if not invite.exists:
            # If not ivited advice to look for the sponsor
            update.message.reply_text("It's closed community for invite only. Please find a sponsor first!")
        else:
            # If invited create the Stellar account and update Firestore
            keypair = st_create_account()
            
            if keypair is None:
                update.message.reply_text("Something went wrong with creation of Stellar account! Admins are notified. Please try later!")
                bot.send_message(admin_chat_id, f"User creation failed: @{username}")
            else:
                users.document(uid).set({'uid': uid, 'username': username, 'chat_id': chat_id, 'secret': keypair.secret, 'public': keypair.public_key})
                update.message.reply_text(f"Your Stellar account cretaed: {keypair.public_key}")
                
                # TODO: Send context dependent hint what to do next
                update.message.reply_text(f"Use /list command to see which assets available around you")


# /invite command wrapper 
def invite_command_handler(update, context):
    """Invite other user to participate in Roundibot."""
    
    if len(context.args) != 1:
        update.message.reply_text("Syntax: /invite <telegram username>")
    else:
        username = update.message.from_user.username.lower()
        ivitee = context.args[0].lower()
        invites.document(ivitee).set({'invited_by': username})
        update.message.reply_text(f"User @{ivitee} invited. He can start using the bot.")
        bot.send_message(admin_chat_id, f"New user @{ivitee} invited by @{username}")
    #TODO: Charge user for the inviting others

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
admin_chat_id = 419686805 # TODO: replace with settings from Firestore
if os.getenv('BOT_ENV') == 'TEST':
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=os.getenv('TELEGRAM_TOKEN'))
    bot = updater.bot

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
dispatcher.add_handler(CommandHandler(["in", "invite"], invite_command_handler))
dispatcher.add_handler(CommandHandler(["he", "help"], help_command_handler))
dispatcher.add_handler(CommandHandler(["is", "issue"], issue_command_handler))
dispatcher.add_handler(CommandHandler(["li", "list"], list_command_handler))
dispatcher.add_handler(CommandHandler(["tr", "trust"], trust_command_handler))
dispatcher.add_handler(CommandHandler(["se", "send"], send_command_handler))
dispatcher.add_handler(CommandHandler(["or", "order"], order_command_handler))
dispatcher.add_handler(CommandHandler(["pa", "pay"], pay_command_handler))
dispatcher.add_handler(CommandHandler(["ba","balance"], balance_command_handler))
dispatcher.add_handler(CommandHandler(["bo","book"], book_command_handler))
dispatcher.add_error_handler(error)
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
