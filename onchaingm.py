from web3 import Web3
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import config


def get_contract_address_onchaingm(chain_name):
    contract_addresses_dict = {
        "eth_sepolia":  "0x905415eb04E331d9edA60c67fcAa36e019Ab3C96",
        'base_sepolia': '0xd932af3476A503ff3B07FDFf1A9B9e3febd29f29',
        "monad":        "0xe48DF32fe1D7d4b73d1Af33A2edd65495945fDcD",
        "mega":         "0x28D63f2386fC39D0B89608Fd25F51B31055B7892",
        'somnia':       '0x7B2865d1387b1a5ce2D2465cfF8c6C3058a66De4',
        "rise":         "0x779F6E324f16604B0F31B2D12a0C2EEeBB7f83F8",
        "moca":         "0x69ff78Ec3A743D040f6D1434737aeb1F67db3eA6",
        "kite":         "0x8Ce0D61503a90CC6dd6ae8F1AAf7FA6e2B32d30f", #poa
        'incentiv':     '0x139c68fC3ffA5685D43d72b5Da5755241b0D0137', #poa
        'camp':         '0x13B01762426C4386D24C0e211fC67b0fc71dcfEE',
        'pharos':       '0x55F8D7108867f71827bEF25B261822dd4df5d9C5',
        '0g':           '0xcdfE091654eb9Bea9406052E9c1Ffe715c6030be',
        'sahara':       '0x7345847282E87fa3Ae842CBdAD4D1b7fAc17B24C', #poa
        'nexus':        '0x0492225322A80f531bd746110b8138d8361B9Fc5',
        'seismic':      '0xe19F5585061452c29f5E187DF93e12eB0794686f',
        'irys':         '',
    }
    return contract_addresses_dict.get(chain_name)

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

def get_tx(web3, chain_name, account_address, native_token, chain_id):
    # Адрес контракта
    contract_address = get_contract_address_onchaingm(chain_name)
    
    # ABI контракта
    abi = [{
    "anonymous": False,
    "inputs": [
        {
            "indexed": False,
            "internalType": "string",
            "name": "greeting",
            "type": "string"
        },
        {
            "indexed": True,
            "internalType": "address",
            "name": "sender",
            "type": "address"
        }
    ],
    "name": "logGM",
    "type": "event"
    }, {
    "inputs": [
        {
            "internalType": "string",
            "name": "greeting",
            "type": "string"
        }
    ],
    "name": "sendGM",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
    }]
    contract = web3.eth.contract(address=contract_address, abi=abi)
    greeting = f"GM"
    try:
        gas_estimate = contract.functions.sendGM(greeting).estimate_gas({'from': account_address})
        gas_limit = gas_estimate + int(gas_estimate * 0.1)  # 10% запас
        print(f"Оценка газа: {gas_estimate}, Лимит газа: {gas_limit}")
    except Exception as e:
        print(f"Ошибка оценки газа: {e}")
        exit()

    # Определяем параметры газа (EIP-1559)
    try:
        max_priority_fee = web3.eth.max_priority_fee  # Рекомендуемая приоритетная комиссия
    except ValueError:
        max_priority_fee = web3.to_wei('2', 'gwei')  # Запасное значение
    try:
        base_fee = web3.eth.get_block('latest')['baseFeePerGas']
        max_fee_per_gas = base_fee + max_priority_fee
        max_fee_limit = web3.to_wei('200', 'gwei')
        print(f"Базовая комиссия: {web3.from_wei(base_fee, 'gwei')} gwei")
        print(f"Приоритетная комиссия: {web3.from_wei(max_priority_fee, 'gwei')} gwei")
        print(f"Максимальная комиссия: {web3.from_wei(max_fee_per_gas, 'gwei')} gwei")

        if max_fee_per_gas > max_fee_limit:
            print("Комиссия слишком высокая, транзакция не отправлена")
            exit()

        # Рассчитываем стоимость
        estimated_cost_wei = gas_limit * max_fee_per_gas
        estimated_cost_eth = web3.from_wei(estimated_cost_wei, 'ether')
        print(f"Оценочная стоимость транзакции: {estimated_cost_eth} {native_token}")

        # Строим транзакцию
        tx_param = {
            'from': account_address,
            'nonce': web3.eth.get_transaction_count(account_address),
            'gas': gas_limit,
            'maxPriorityFeePerGas': max_priority_fee,
            'maxFeePerGas': max_fee_per_gas,
            'chainId': chain_id
        }
    except Exception as e:
        print(f'обработанная ошибка:\n{e}')
        gas_price = web3.eth.gas_price
        print(f"Gas Price: {web3.from_wei(gas_price, 'gwei')} gwei")
        tx_param = {
            'from': account_address,
            'nonce': web3.eth.get_transaction_count(account_address),
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': chain_id
        }
    return contract.functions.sendGM(greeting).build_transaction(tx_param)

def sendGM(chain_name):
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
    print(f"Подключено к {chain_name} ID: {chain_id}")
    native_token = 'ETH' # добавить функцию получение имени токена

    balance_eth = get_balance(web3, account_address)
    print(f"Баланс: {balance_eth} ETH")
    tx = get_tx(web3, chain_name, account_address, native_token, chain_id)
    # Подписываем и отправляем
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Транзакция отправлена: {tx_hash.hex()}")

    # Ждём подтверждения
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Транзакция подтверждена в блоке: {receipt.blockNumber}\n")

def main(chain_list):
    for name in chain_list:
        sendGM(name)

if __name__ == "__main__":
    chain_list = ['irys', 'eth_sepolia', 'monad', 'mega', 'somnia', 'rise', 'base_sepolia', 'moca', 'kite', 'incentiv', 'camp', 'pharos', '0g', 'sahara', 'nexus']
    #chain_list = ['seismic', ] 
    main(chain_list)
    print(f'script done\n')