from web3 import Web3
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import config


def get_chain_rpc(chain_name):
    eth_sepolia = 'https://eth-sepolia.g.alchemy.com/v2/OXUlCB_5QwG0GR_gJhmTrehy4RiUtn8Q'
    monad_test  = 'https://monad-testnet.g.alchemy.com/v2/OXUlCB_5QwG0GR_gJhmTrehy4RiUtn8Q'
    mega        = 'https://carrot.megaeth.com/rpc'
    somnia      = 'https://dream-rpc.somnia.network'
    return somnia

def web3gm(chain_name):
    rpc_url = get_chain_rpc(chain_name)
    web3 = Web3(Web3.HTTPProvider(rpc_url))

    account_address = config.main_addr
    # Преобразуем в checksum-формат
    checksum_address = Web3.to_checksum_address(account_address)
    account_address = Web3.to_checksum_address(account_address)

    private_key = config.PRIVATE_KEY_MAIN
    if not private_key:
        print("Приватный ключ не найден")
        exit()

    # Проверяем подключение
    if web3.is_connected():
        print("Подключено")
        # Получаем chainId
        chain_id = web3.eth.chain_id
        print(f"Chain ID: {chain_id}")
        native_token = 'ETH' # добавить функцию получение имени токена
        # Получаем баланс в wei
        balance_wei = web3.eth.get_balance(checksum_address)
        print(f'wei: {balance_wei}')
        
        # Конвертируем в ETH
        balance_eth = web3.from_wei(balance_wei, 'ether')
        print(f"Баланс: {balance_eth} ETH")

        # Адрес контракта
        contract_address = "0x905415eb04E331d9edA60c67fcAa36e019Ab3C96" #sepolia
        contract_address = "0xe48DF32fe1D7d4b73d1Af33A2edd65495945fDcD" #monad
        contract_address = "0x28D63f2386fC39D0B89608Fd25F51B31055B7892" #mega
        
        # ABI контракта
        abi = [
	{
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
	},
	{
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
	}
]
        contract = web3.eth.contract(address=contract_address, abi=abi)
        greeting = "GM"
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
        base_fee = web3.eth.get_block('latest')['baseFeePerGas']
        max_fee_per_gas = base_fee + max_priority_fee
        max_fee_limit = web3.to_wei('150', 'gwei')

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
        tx = contract.functions.sendGM(greeting).build_transaction({
            'from': account_address,
            'nonce': web3.eth.get_transaction_count(account_address),
            'gas': gas_limit,
            'maxPriorityFeePerGas': max_priority_fee,
            'maxFeePerGas': max_fee_per_gas,
            'chainId': chain_id
        })

        # Подписываем и отправляем
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Транзакция отправлена: {tx_hash.hex()}")

        # Ждём подтверждения
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Транзакция подтверждена в блоке: {receipt.blockNumber}")
        pass

def main(chain_list):
    for name in chain_list:
        web3gm(name)
    pass

if __name__ == "__main__":
    chain_list = ['sepolia', ]
    main(chain_list)
    print(f'script done\n')