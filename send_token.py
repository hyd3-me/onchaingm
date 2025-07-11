from web3 import Web3
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import config


def get_chain_rpc(chain_name):
    return config.rpc_name_dict.get(chain_name)

def getWeb3(chain_name):
    rpc_url = get_chain_rpc(chain_name)
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    # Проверяем подключение
    if not web3.is_connected():
        print(f'failed to connect to the {chain_name}\n')
        return
    return web3

def get_balance(web3, account_address):
    # Получаем баланс в wei
    balance_wei = web3.eth.get_balance(account_address)
    # Конвертируем в ETH
    return web3.from_wei(balance_wei, 'ether')

def get_tx_param(web3, account_address, chain_id, amount_wei, nonce):
    # Определяем параметры газа (EIP-1559)
    gas_limit = 21000 # Стандартный лимит газа для простого перевода
    try:
        max_priority_fee = web3.eth.max_priority_fee  # Рекомендуемая приоритетная комиссия
    except ValueError:
        max_priority_fee = web3.to_wei('2', 'gwei')  # Запасное значение
    try:
        base_fee = web3.eth.get_block('latest')['baseFeePerGas']
        max_fee_per_gas = base_fee + max_priority_fee
        max_fee_limit = web3.to_wei('150', 'gwei')
        print(f"Базовая комиссия: {web3.from_wei(base_fee, 'gwei')} gwei")
        print(f"Приоритетная комиссия: {web3.from_wei(max_priority_fee, 'gwei')} gwei")
        print(f"Максимальная комиссия: {web3.from_wei(max_fee_per_gas, 'gwei')} gwei")

        if max_fee_per_gas > max_fee_limit:
            print("Комиссия слишком высокая, транзакция не отправлена")
            exit()
        
        # Строим транзакцию
        tx_param = {
            'maxPriorityFeePerGas': max_priority_fee,
            'maxFeePerGas': max_fee_per_gas,
            'from': account_address,
            'to': account_address,
            'value': amount_wei,
            'nonce': nonce,
            'gas': gas_limit,
            'chainId': chain_id
        }
    except Exception as e:
        print(f'обработанная ошибка:\n{e}')
        gas_price = web3.eth.gas_price
        print(f"Gas Price: {web3.from_wei(gas_price, 'gwei')} gwei")
        tx_param = {
            'from': account_address,
            'to': account_address,
            'value': amount_wei,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': chain_id
        }
    return tx_param

def send_token(chain_name, _count=5):
    web3 = getWeb3(chain_name)
    if not web3:
        return
    private_key = config.PRIVATE_KEY_MAIN
    if not private_key:
        print("Приватный ключ не найден")
        return
    account_address = config.main_addr
    # Преобразуем в checksum-формат
    account_address = Web3.to_checksum_address(account_address)
    # Получаем chainId
    chain_id = web3.eth.chain_id
    print(f"\nПодключено к {chain_name} ID: {chain_id}")
    native_token = 'ETH' # добавить функцию получение имени токена

    balance_eth = get_balance(web3, account_address)
    print(f"Баланс: {balance_eth} ETH")

    # Конвертируем 0.00001 токена в wei
    amount_wei = web3.to_wei(0.00001, 'ether')
    nonce = web3.eth.get_transaction_count(account_address)
    for i in range(_count):
        try:
            tx_params = get_tx_param(web3, account_address, chain_id, amount_wei, nonce)
            # Подписываем транзакцию
            signed_tx = web3.eth.account.sign_transaction(tx_params, private_key)
            # Отправляем транзакцию
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"Транзакция отправлена: {tx_hash.hex()}")

            # Ждём подтверждения
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Транзакция подтверждена в блоке: {receipt.blockNumber}\n")
        except Exception as e:
            print(f'обработанная ошибка в цикле функции send_token:\n{e}')
        nonce += 1

def main(chain_list):
    for name in chain_list:
        send_token(name)

if __name__ == "__main__":
    chain_list = ['irys', 'eth_sepolia', 'monad', 'mega', 'somnia', 'rise', 'base_sepolia', 'moca', 'kite', 'incentiv', 'camp', 'pharos', '0g', 'sahara', 'nexus']
    #chain_list = ['rise', ] 
    main(chain_list)
    print(f'script done\n\n')