#!/usr/bin/env python3
#
# Copyright Soramitsu Co., Ltd. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import binascii
import time
import random
from iroha import IrohaCrypto
from iroha import Iroha, IrohaGrpc
from iroha.primitive_pb2 import can_set_my_account_detail
import sys

if sys.version_info[0] < 3:
    raise Exception('Python 3 or a more recent version is required.')

ADMIN_ACCOUNT_ID = "admin@test"
USER_ACCOUNT_NAME = "userone{}".format(random.randint(1,99999))
USER_ACCOUNT_ID = "{}@domain".format(USER_ACCOUNT_NAME)


IROHA_HOST_ADDR = os.getenv('IROHA_HOST_ADDR', '127.0.0.1')
IROHA_PORT = os.getenv('IROHA_PORT', '50051')
ADMIN_ACCOUNT_ID = os.getenv('ADMIN_ACCOUNT_ID', 'admin@test')
ADMIN_PRIVATE_KEY = os.getenv(
    'ADMIN_PRIVATE_KEY', 'f101537e319568c765b2cc89698325604991dca57b9716b58016b253506cab70')

user_private_key = IrohaCrypto.private_key()
user_public_key = IrohaCrypto.derive_public_key(user_private_key)
iroha = Iroha(ADMIN_ACCOUNT_ID)
net = IrohaGrpc('{}:{}'.format(IROHA_HOST_ADDR, IROHA_PORT))


def trace(func):
    """
    A decorator for tracing methods' begin/end execution points
    """

    def tracer(*args, **kwargs):
        name = func.__name__
        print('\tEntering "{}"'.format(name))
        result = func(*args, **kwargs)
        print('\tLeaving "{}"'.format(name))
        return result

    return tracer


@trace
def send_transaction_and_print_status(transaction):
    hex_hash = binascii.hexlify(IrohaCrypto.hash(transaction))
    print('Transaction hash = {}, creator = {}'.format(
        hex_hash, transaction.payload.reduced_payload.creator_account_id))
    net.send_tx(transaction)
    time.sleep(1)
    for status in net.tx_status_stream(transaction):
        print(status)


@trace
def create_domain_and_asset():
    """
    Creates domain 'domain' and asset 'coin#domain' with precision 2
    """
    commands = [
        iroha.command('CreateDomain', domain_id='domain', default_role='user'),
        iroha.command('CreateAsset', asset_name='coin',
                      domain_id='domain', precision=2)
    ]
    tx = IrohaCrypto.sign_transaction(
        iroha.transaction(commands), ADMIN_PRIVATE_KEY)
    send_transaction_and_print_status(tx)


@trace
def add_coin_to_admin():
    """
    Add 1000.00 units of 'coin#domain' to 'admin@test'
    """
    tx = iroha.transaction([
        iroha.command('AddAssetQuantity',
                      asset_id='coin#domain', amount='1000.00')
    ])
    IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
    send_transaction_and_print_status(tx)


@trace
def create_account_userone():
    """
    Create account 'userone@domain'
    """
    tx = iroha.transaction([
        iroha.command('CreateAccount', account_name=USER_ACCOUNT_NAME, domain_id='domain',
                      public_key=user_public_key)
    ])
    IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
    send_transaction_and_print_status(tx)


@trace
def transfer_coin_from_admin_to_userone():
    """
    Transfer 2.00 'coin#domain' from 'admin@test' to 'userone@domain'
    """
    tx = iroha.transaction([
        iroha.command('TransferAsset', src_account_id='admin@test', dest_account_id=USER_ACCOUNT_ID,
                      asset_id='coin#domain', description='init top up', amount='2.00')
    ])
    IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
    send_transaction_and_print_status(tx)

@trace
def transfer_coin_from_userone_to_admin(send_amount='1.10'):
    """
    Transfer 1.10 'coin#domain' from 'userone@domain' to 'admin@test'
    """
    tx = iroha.transaction([
        iroha.command('TransferAsset', src_account_id=USER_ACCOUNT_ID, dest_account_id='admin@test',
                      asset_id='coin#domain', description='get back', amount=send_amount)
    ], creator_account=USER_ACCOUNT_ID)
    IrohaCrypto.sign_transaction(tx, user_private_key)
    send_transaction_and_print_status(tx)

@trace
def userone_grants_to_admin_set_account_detail_permission():
    """
    Make admin@test able to set detail to userone@domain
    """
    tx = iroha.transaction([
        iroha.command('GrantPermission', account_id='admin@test',
                      permission=can_set_my_account_detail)
    ], creator_account=USER_ACCOUNT_ID)
    IrohaCrypto.sign_transaction(tx, user_private_key)
    send_transaction_and_print_status(tx)


@trace
def set_age_to_userone():
    """
    Set age to userone@domain by admin@test
    """
    tx = iroha.transaction([
        iroha.command('SetAccountDetail',
                      account_id=USER_ACCOUNT_ID, key='age', value='18')
    ])
    IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
    send_transaction_and_print_status(tx)


@trace
def get_coin_info():
    """
    Get asset info for coin#domain
    :return:
    """
    query = iroha.query('GetAssetInfo', asset_id='coin#domain')
    IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

    response = net.send_query(query)
    data = response.asset_response.asset
    print('Asset id = {}, precision = {}'.format(data.asset_id, data.precision))


@trace
def get_account_assets():
    """
    List all the assets of userone@domain
    """
    query = iroha.query('GetAccountAssets', account_id=USER_ACCOUNT_ID)
    IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

    response = net.send_query(query)
    data = response.account_assets_response.account_assets
    for asset in data:
        print('Asset id = {}, balance = {}'.format(
            asset.asset_id, asset.balance))

@trace
def get_account_asset_transactions():
    """
    List all the transactions of userone@domain
    """
    query = iroha.query('GetAccountAssetTransactions', account_id=USER_ACCOUNT_ID, asset_id='coin#domain', page_size=10)
    IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

    response = net.send_query(query)
    data = response.transactions_page_response.transactions
    print('Transaction amount = {}'.format(len(data)))
    for transaction in data:
        print('Transaction payload = {}'.format(
            transaction.payload))

@trace
def get_account_transactions():
    """
    List all the transactions of userone@domain
    """
    query = iroha.query('GetAccountTransactions', account_id=USER_ACCOUNT_ID)
    IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

    response = net.send_query(query)
    data = response.transactions_response.transactions
    print('Transaction amount = {}'.format(len(data)))
    for transaction in data:
        print('Transaction payload = {}'.format(
            transaction.payload))

@trace
def get_userone_details():
    """
    Get all the kv-storage entries for userone@domain
    """
    query = iroha.query('GetAccountDetail', account_id=USER_ACCOUNT_ID)
    IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

    response = net.send_query(query)
    data = response.account_detail_response
    print('Account id = {}, details = {}'.format(USER_ACCOUNT_ID, data.detail))


create_domain_and_asset()
add_coin_to_admin()
create_account_userone()
transfer_coin_from_admin_to_userone()
transfer_coin_from_userone_to_admin()
userone_grants_to_admin_set_account_detail_permission()
set_age_to_userone()
get_coin_info()
get_account_assets()
get_userone_details()
get_account_transactions()
get_account_asset_transactions()

print('done')
