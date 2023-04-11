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
def st_create_account(funding_keypair = None, starting_balance = 5):
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
        print(f'st_trust_asset: Set trust failed:{type(err)}\n{err}')
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
        print(f'st_send: Send failed:{type(err)}\n{err}')
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
        print(f'st_issue_asset: Asset issue failed:{type(err)}\n{err}')
        return None

    
# Function to build the list of Assets
def st_build_path(path):
    return [Asset(p['asset_code'], p['asset_issuer']) for p in path]


# Function to find payments paths
def st_paths(account_public, asset, amount):
    try:
        res = stellar.strict_receive_paths(account_public, asset, "%.5f" % amount).call()
        paths = [{'code': p['source_asset_code'], 'issuer': p['source_asset_issuer'], 'amount': float(p['source_amount']), 'path': st_build_path(p['path'])} for p in res['_embedded']['records']]
        return paths
    except Exception as err:
        print(f'st_paths: path search failed:{type(err)}\n{err}')
        return []


# Function to create an asset and transfer to distribution account
# Return: issuing_keypair
def st_send_strict(source_keypair, target_public, send_asset, send_max, dest_asset, dest_amount, path):
    try:
        source_public = source_keypair.public_key
        source_account = stellar.load_account(source_public)

        # Second, the issuing account actually sends a payment using the asset.
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=stellar_passphrase,
                base_fee=100,
            )
            .append_path_payment_strict_receive_op(
                destination=target_public, 
                send_asset=send_asset, 
                send_max="%.5f" % send_max, 
                dest_asset=dest_asset, 
                dest_amount="%.5f" % dest_amount, 
                path=path,
            )
            .set_timeout(100)
            .build()
        )
        transaction.sign(source_keypair)
        resp = stellar.submit_transaction(transaction)
        if resp['successful'] != True:
            print(f'st_send_strict: Trust line transaction failed:\n{resp}')
            return None
        else:
            return True
    except Exception as err:
        print(f'st_send_strict: path payment failed:{type(err)}\n{err}')
        return None

    
# Function to show balances of the account
def st_balance(account_public):
    account = stellar.accounts().account_id(account_public).call()
    #print('DEBUG!!!:', account['balances'])
    balances = [{'asset_code': b['asset_code'], 'asset_issuer': b['asset_issuer'], 'balance': float(b['balance'])} for b in account['balances'] if b['asset_type'] not in ['native', 'liquidity_pool_shares']]
    return balances


# Function to offer/order an exchange of one asset to another
def st_buy_offer(source_keypair, selling_asset, buying_asset, selling_amount, buying_amount, offer_id=0):
    try:
        source_public = source_keypair.public_key
        source_account = stellar.load_account(source_public)

        # Second, the issuing account actually sends a payment using the asset.
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=stellar_passphrase,
                base_fee=100,
            )
            .append_manage_buy_offer_op(
                selling=selling_asset, 
                buying=buying_asset, 
                amount="%.5f" % buying_amount, 
                price="%.5f" % (selling_amount/buying_amount), 
                offer_id=offer_id,
            )
            .set_timeout(100)
            .build()
        )
        transaction.sign(source_keypair)
        resp = stellar.submit_transaction(transaction)
        if resp['successful'] != True:
            print(f'Offer transaction failed:\n{resp}')
            return None
        else:
            return True
    except Exception as err:
        print(f'st_buy_offer: offer creation failed:{type(err)}\n{err}')
        return None
 

# Function to offer/order an exchange of one asset to another
def st_cancel_offer(source_keypair, offer_id):
    try:
        source_public = source_keypair.public_key
        source_account = stellar.load_account(source_public)

        res = stellar.offers().offer(offer_id).call()
        print('DEBUG!!!: offers', res['_embedded']['records'])
        #offers = [{'id': o['id'], 'seller': o['seller'], 'selling': o['selling']['asset_code'], 'buying': o['buying']['asset_code'], 'selling_amount': float(o['amount']), 'buying_amount': float(o['amount']) * float(o['price'])} for o in res['_embedded']['records']]
        offer = res['_embedded']['records'][0]
        print('DEBUG!! offer', offer)
        selling_asset = Asset(offer['selling']['asset_code'], offer['selling']['issuer'])
        buying_asset = Asset(offer['buying']['asset_code'], offer['buying']['issuer'])

        # Second, the issuing account actually sends a payment using the asset.
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=stellar_passphrase,
                base_fee=100,
            )
            .append_manage_buy_offer_op(
                selling=selling_asset, 
                buying=buying_asset, 
                amount="0", 
                offer_id=offer_id,
            )
            .set_timeout(100)
            .build()
        )
        transaction.sign(source_keypair)
        resp = stellar.submit_transaction(transaction)
        if resp['successful'] != True:
            print(f'Offer transaction failed:\n{resp}')
            return None
        else:
            return True
    except Exception as err:
        print(f'st_cancel_offer: offer cancelation failed:{type(err)}\n{err}')
        return None
 

# Function to show balances of the account
def st_book(account_public):
    try:
        res = stellar.offers().for_account(account_public).call()
        print('DEBUG!!!: offers', res['_embedded']['records'])
        offers = [{'id': o['id'], 'seller': o['seller'], 'selling': o['selling']['asset_code'], 'buying': o['buying']['asset_code'], 'selling_amount': float(o['amount']), 'buying_amount': float(o['amount']) * float(o['price'])} for o in res['_embedded']['records']]
        return offers
    except Exception as err:
        print(f'st_book: offer request failed:{type(err)}\n{err}')
        return None
