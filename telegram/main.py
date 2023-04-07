import os
import json
import traceback
import functions_framework
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import Dispatcher, Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from stellar_sdk import Keypair, Asset
from stellar import st_create_account, st_issue_asset, st_send, st_trust_asset


# Initialize Firestore client
from google.cloud import firestore
db = firestore.Client()
users = db.collection(u'users')
invites = db.collection(u'invites')
assets = db.collection(u'assets')


# Function to check if string is number
def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

# Strip leading @ if any
def strip_user(s):
    if s[0] == '@':
        s = s[1:]
    return s.lower()

    
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

    # Check a syntax
    if len(context.args) != 1:
        update.message.reply_text("Syntax: /invite <telegram username>")
        return
    
    # Check if user is registered in Firebase
    uid = f"{update.message.from_user.id}"
    user_rec = users.document(uid).get()
    if not user_rec.exists:
        update.message.reply_text("You are not registered yet. Please use command /start")
        return

    username = update.message.from_user.username.lower()
    ivitee = strip_user(context.args[0])
        
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
    """Issue new asset or additional amount of existing one."""

    # Check a sintax
    if len(context.args) != 2 or not context.args[1].isnumeric():
        update.message.reply_text("Syntax: /issue <asset code> <quantity>")
        return
    
    # Check if user is registered in Firebase
    uid = f"{update.message.from_user.id}"
    user_rec = users.document(uid).get()
    user_info = user_rec.to_dict()
    
    if not user_rec.exists:
        update.message.reply_text("You are not registered yet. Please use command /start")
        return

    #TODO: Check if user has trusted assets and balances if not ask to use other's assets first
    
    username = update.message.from_user.username.lower()
    asset_code = context.args[0]
    quantity = int(context.args[1])

    # Check if asset code is exist
    asset_rec = assets.document(asset_code).get()
    if asset_rec.exists:
        asset_info = asset_rec.to_dict()

        # If exist and belong to current user issue extra tokens
        if asset_info['issued_by'] == username:
            issuer_keypair = Keypair.from_secret(asset_info['secret'])
            res = st_send(issuer_keypair, user_info['public'], asset_code, issuer_keypair.public_key, quantity)
            if res:
                update.message.reply_text(f"{quantity} of {asset_code} issued and transfered to your account. Use /balance to check it.")
            else:
                update.message.reply_text(f"Something went wrong. Please try again later. Admins are informed!")
                bot.send_message(admin_chat_id, f"User @{username} fail to issue extra quantity of asset {asset_code}")
        else:
            update.message.reply_text(f"Asset code {asset_code} already in used. Please use another one.")
    else:
        # If not exist create and issue tokens
        issuer_keypair = st_issue_asset(Keypair.from_secret(user_info['secret']), quantity, asset_code)
        if issuer_keypair is None:
            update.message.reply_text(f"Something went wrong. Please try again later. Admins are informed!")
            bot.send_message(admin_chat_id, f"User @{username} fail to create asset {asset_code}")
        else:
            assets.document(asset_code).set({'code': asset_code, 'public': issuer_keypair.public_key, 'secret': issuer_keypair.secret, 'issued_by': username})
            update.message.reply_text(f"{quantity} of {asset_code} issued and transfered to your account. Use /balance to check it.")
            update.message.reply_text(f"To be able to receive your tokens other users have to run /trust {asset_code} command.")
            bot.send_message(admin_chat_id, f"New asset {asset_code} created by @{username}")

            
# /list command wrapper 
def list_command_handler(update, context):
    """Send the list of assets available via bot."""
    #TODO: send list of available tokens
    assets_stream = assets.stream()

    for a in assets_stream:
        asset_info = a.to_dict()
        update.message.reply_text(f"{a.id} issued by @{asset_info['issued_by']}")
    
    update.message.reply_text("Use /trust <asset code> or /trust <asset code> <quantity> to trust the token")


# /trust command wrapper 
def trust_command_handler(update, context):
    """Trust an asset in order to use it."""
    # Check a sintax
    if len(context.args) != 1:
        update.message.reply_text("Syntax: /trust <asset code>") # TODO: Add amount to trust
        return
    
    # Check if user is registered in Firebase
    uid = f"{update.message.from_user.id}"
    username = update.message.from_user.username.lower()
    asset_code = context.args[0]

    user_rec = users.document(uid).get()
    user_info = user_rec.to_dict()
    
    if not user_rec.exists:
        update.message.reply_text("You are not registered yet. Please use command /start")
        return

    # Check if asset code is exist
    asset_rec = assets.document(asset_code).get()
    if not asset_rec.exists:
        update.message.reply_text(f"Asset {asset_code} not registered. Please check the list of available assets with the /list command.")
        return        
        
    asset_info = asset_rec.to_dict()

    # Set trust to the asset
    res = st_trust_asset(Keypair.from_secret(user_info['secret']), asset_code, asset_info['public'])
    if res:
        update.message.reply_text(f"Trust line added. You can receive {asset_code} tokens. Ask holder to /send {asset_code} @{username}")
        # TODO: if user has non zero balances check paths to the new asset and show how to order it
    else:
        update.message.reply_text(f"Something went wrong. Please try again later. Admins are informed!")
        bot.send_message(admin_chat_id, f"User @{username} fail to set a trust line for asset {asset_code}")

    
# /send command wrapper 
def send_command_handler(update, context):
    """Send tokens to another user."""
    # Check a sintax
    if len(context.args) != 3 or not isfloat(context.args[0]):
        update.message.reply_text("Syntax: /send <amount> <asset code> <username>")
        return
    
    # Check if user is registered in Firebase
    uid = f"{update.message.from_user.id}"
    username = update.message.from_user.username.lower()
    amount = float(context.args[0])
    asset_code = context.args[1]

    user_rec = users.document(uid).get()
    user_info = user_rec.to_dict()
    
    if not user_rec.exists:
        update.message.reply_text("You are not registered yet. Please use command /start")
        return

    # Check if asset code is exist
    asset_rec = assets.document(asset_code).get()
    if not asset_rec.exists:
        update.message.reply_text(f"Asset {asset_code} not registered. Please check the list of available assets with the /list command.")
        return        
        
    asset_info = asset_rec.to_dict()
    asset = Asset(asset_code, asset_info['public'])

    # Check if recepient exist and has a trust line for given asset
    recepient = strip_user(context.args[2])
    recepients_ref = users.where('username', '==', recepient).stream()
    recepients = [d for d in recepients_ref]

    if len(recepients) == 0:
        update.message.reply_text(f"Recepient user @{recepient} does not exist.")
        print(f"send_command_handler: Recepient user @{recepient} does not exist.")
        return
    elif len(recepients) > 1:
        update.message.reply_text(f"Duplicate username @{recepient}. Transfer could not be made.")
        print(f"send_command_handler: Duplicate username @{recepient}. Transfer could not be made.")
        return

    recipient_info = recepients[0].to_dict()
    
    # Search available paths to pay given tokens
    paths = st_paths(user_info['public'], asset, amount)
      
    # If no paths available inform users  
    if len(paths) == 0:
        update.message.reply_text(f"No conversion path available to asset {asset_code}.") 
        # TODO: Analize why no paths: zero balance of accounts, no demand for own tokens
        return

    # If more than 1 path send a menu with choice how to pay
    keyboard = [[InlineKeyboardButton(f"{p['source_asset_code']} ({p['source_amount']})", callback_data="%d" % i)] for i, p in enumerate(paths)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"Please confirm your asset and amount to pay {amount} to @{recepient}", reply_markup=reply_markup)        
    
    #update.message.reply_text("Use /order <amount> <buying asset> <amount> <selling assed> to exchange tokens to another token")


# Parse inline callbacks for buttons
def button_callback_handler(update, context):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
                              
    print('DEBUG!!!', query)                          

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    query.edit_message_text(text=f"Selected option: {query.data}")    
    # Send given number of the tokens to a specified user via path payment
    
    
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
dispatcher.add_handler(CallbackQueryHandler(button_callback_handler))
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
