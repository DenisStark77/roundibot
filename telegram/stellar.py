import os
import requests
from decimal import Decimal
from stellar_sdk import Keypair, Server, Asset, Network, TransactionBuilder, LiquidityPoolAsset

# Initialize Stellar client
starting_balance = 3 
stellar_seed = os.getenv('STELLAR_SEED')
if os.getenv('BOT_ENV') == 'TEST':
    stellar = Server(horizon_url="https://horizon-testnet.stellar.org")
    stellar_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
else:
    stellar = Server(horizon_url="https://horizon.stellar.org")
    stellar_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE
bot_keypair = Keypair.from_secret(stellar_seed)
bot_public = bot_keypair.public_key


# Function to create an account
def st_create_account():
    # Generate new account
    keypair = Keypair.random()

    # Sends funds to source new account
    bot_account = stellar.load_account(bot_public)
    transaction = (
        TransactionBuilder(
            source_account=bot_account,
            network_passphrase=stellar_passphrase,
            base_fee=100,
        )
        .append_payment_op(
            destination=keypair.public_key,
            asset='native',
            amount="%d" % starting_balance,
        )
        .set_timeout(100)
        .build()
    )
    transaction.sign(bot_keypair)
    resp = stellar.submit_transaction(transaction)
    if resp['successful'] != True:
        print(f'Initial funds load failed:\n{resp}')
        return None
    else:
        return keypair
