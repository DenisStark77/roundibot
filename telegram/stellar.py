import os
import requests
from decimal import Decimal
from stellar_sdk import Keypair, Server, Asset, Network, TransactionBuilder, LiquidityPoolAsset

# Initialize Stellar client
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
def st_create_account(funding_keypair = None, starting_balance = 3):
    if funding_keypair is None:
        funding_keypair = bot_keypair
    
    try:
        # Generate new account
        keypair = Keypair.random()

        # Sends funds to source new account
        funding_account = stellar.load_account(funding_keypair.public_key)
        transaction = (
            TransactionBuilder(
                source_account=funding_account,
                network_passphrase=stellar_passphrase,
                base_fee=100,
            )
            .append_create_account_op(
                destination=keypair.public_key, starting_balance="%d" % starting_balance
            )
            .set_timeout(100)
            .build()
        )
        transaction.sign(funding_keypair)
        resp = stellar.submit_transaction(transaction)
        if resp['successful'] != True:
            print(f'st_create_account: Initial funds load failed:\n{resp}')
            return None
        else:
            return keypair
    except Exception as err:
        print(f'st_create_account: Account creation failed:{type(err)}\n{err}')
        return None

    
# Function to set a trust to an asset
# Return: issuing_keypair
def st_trust_asset(distributor_keypair, code, issuing_public, amount=None):
    try:
        asset = Asset(code, issuing_public)
        distributor_public = distributor_keypair.public_key
        distributor_account = stellar.load_account(distributor_public)

        # First, the receiving account must trust the asset
        if amount is not None:
            transaction = (
                TransactionBuilder(
                    source_account=distributor_account,
                    network_passphrase=stellar_passphrase,
                    base_fee=100,
                )
                #  The `changeTrust` operation creates (or alters) a trustline
                #  The `limit` parameter below is optional
                .append_change_trust_op(asset=asset, limit="%d" % amount)
                .set_timeout(100)
                .build()
            )
        else:
            transaction = (
                TransactionBuilder(
                    source_account=distributor_account,
                    network_passphrase=stellar_passphrase,
                    base_fee=100,
                )
                #  The `changeTrust` operation creates (or alters) a trustline
                #  The `limit` parameter below is optional
                .append_change_trust_op(asset=asset)
                .set_timeout(100)
                .build()
            )

        transaction.sign(distributor_keypair)
        resp = stellar.submit_transaction(transaction)
        if resp['successful'] != True:
            print(f'st_trust_asset: Trust line transaction failed:\n{resp}')
            return False
        else:  
            return True
    except Exception as err:
        print(f'st_trust_asset: Acoount creation failed:{type(err)}\n{err}')
        return None


# Function to transfer asset to another account
# Return: True if success
def st_send(source_keypair, target_public, code, issuing_public, amount):
    try:
        source_public = source_keypair.public_key

        # Create Asset
        asset = Asset(code, issuing_public)

        source_account = stellar.load_account(source_public)
        # Second, the issuing account actually sends a payment using the asset.
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=stellar_passphrase,
                base_fee=100,
            )
            .append_payment_op(
                destination=target_public,
                asset=asset,
                amount="%d" % amount,
            )
            .set_timeout(100)
            .build()
        )
        transaction.sign(source_keypair)
        resp = stellar.submit_transaction(transaction)
        if resp['successful'] != True:
            print(f'st_send: Send transaction failed:\n{resp}')
            return None
        else:
            return True
    except Exception as err:
        print(f'st_create_account: Acoount creation failed:{type(err)}\n{err}')
        return None
    
    
# Function to create an asset and transfer to distribution account
# Return: issuing_keypair
def st_issue_asset(distributor_keypair, amount, code):
    try:
        # Create an issuing account
        issuing_keypair = st_create_account(starting_balance=2) # TODO: Fund issuing contract from the current user
        
        if issuing_keypair is None:
            print(f'st_issue_asset: Creation of issuing account failed {distributor_keypair.public_key}')
            return None

        issuing_public = issuing_keypair.public_key
        distributor_public = distributor_keypair.public_key
        distributor_account = stellar.load_account(distributor_public)

        # First, the receiving account must trust the asset
        if not st_trust_asset(distributor_keypair, code, issuing_public):
            return None

        if not st_send(issuing_keypair, distributor_public, code, issuing_public, amount):
            return None

        return issuing_keypair
    except Exception as err:
        print(f'st_create_account: Acoount creation failed:{type(err)}\n{err}')
        return None
