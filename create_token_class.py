import os
import sys
import time
import random
import hashlib
import logging
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from solcx import compile_source, install_solc, set_solc_version


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Подключаем конфигурацию
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import config

# Solidity-код контракта
SOLIDITY_CODE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    constructor(string memory name, string memory symbol, uint256 initialSupply) ERC20(name, symbol) {
        _mint(msg.sender, initialSupply);
    }
}
"""

# Пользовательское исключение
class NetworkHandlerError(Exception):
    pass

class NetworkHandler:
    def __init__(self, chain_name):
        logging.info(f"Подключаемся к: {chain_name}")
        self.chain_name = chain_name
        self.rpc_url = config.rpc_name_dict.get(chain_name)
        self.web3 = self._connect()
        if not self.web3:
            raise NetworkHandlerError(f"Не удалось подключиться к {chain_name}")
        self.account_address = Web3.to_checksum_address(config.main_addr)
        if not self.account_address:
            raise NetworkHandlerError(f"Адрес аккаунта не найден для сети {chain_name}")
        self.private_key = config.PRIVATE_KEY_MAIN
        if not config.PRIVATE_KEY_MAIN:
            raise NetworkHandlerError(f"Приватный ключ не найден для сети {chain_name}")
        

    def _connect(self):
        """Подключается к сети и возвращает объект Web3."""
        if not self.rpc_url:
            raise NetworkHandlerError(f"RPC для сети {chain_name} не найден")
        web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.is_pos = self.is_pos_network(web3)
        self.chain_id = web3.eth.chain_id if web3 else None
        if not self.is_pos:
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if not web3.is_connected():
            logging.error(f"Не удалось подключиться к {self.chain_name}")
            return None
        else:
            logging.info(f"Подключено к {self.chain_name} ID: {self.chain_id}")
        return web3

    def is_pos_network(self, web3):
        """Проверяет, является ли сеть PoS."""
        try:
            block = web3.eth.get_block('latest')
            return len(block.get('extraData', b'')) < 33
        except Exception as e:
            logging.warning(f"Ошибка проверки сети, считаем PoA: {e}")
            return False

    def get_balance(self):
        """Возвращает баланс аккаунта в wei."""
        try:
            return self.web3.eth.get_balance(self.account_address)
        except Exception as e:
            logging.error(f"Ошибка получения баланса: {e}")
            return 0
    
    def to_ether(self, wei):
        return self.web3.from_wei(wei, 'ether')

    def get_tx_params(self, gas_limit, nonce):
        """Создаёт параметры транзакции с учётом типа сети."""
        if not self.web3:
            return None
        try:
            if self.is_pos:
                max_priority_fee = self.web3.eth.max_priority_fee
                base_fee = self.web3.eth.get_block('latest')['baseFeePerGas']
                max_fee_per_gas = base_fee + max_priority_fee
                max_fee_limit = self.web3.to_wei('200', 'gwei')
                if max_fee_per_gas > max_fee_limit:
                    logging.warning("Комиссия слишком высокая")
                    return None
                logging.info(f"Базовая комиссия: {self.web3.from_wei(base_fee, 'gwei')} gwei")
                logging.info(f"Приоритетная комиссия: {self.web3.from_wei(max_priority_fee, 'gwei')} gwei")
                return {
                    'from': self.account_address,
                    'nonce': nonce,
                    'gas': gas_limit,
                    'maxFeePerGas': max_fee_per_gas,
                    'maxPriorityFeePerGas': max_priority_fee,
                    'chainId': self.chain_id
                    }  
            else:
                gas_price = self.web3.eth.gas_price
                logging.info(f"Gas Price: {self.web3.from_wei(gas_price, 'gwei')} gwei")
                return {
                    'from': self.account_address,
                    'nonce': nonce,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'chainId': self.chain_id
                    }

        except Exception as e:
            logging.error(f"Ошибка создания параметров транзакции: {e}")
            return None

def compile_contract(solidity_code):
    """Компилирует Solidity-код."""
    try:
        install_solc('0.8.26')
        set_solc_version('0.8.26')
        npm_path = os.path.join(os.path.expanduser("~"), "node_modules")
        compiled = compile_source(solidity_code, output_values=['abi', 'bin'], 
                                 import_remappings={"@openzeppelin": f"{npm_path}/@openzeppelin"})
        contract_id, contract_data = compiled.popitem()
        if not contract_data:
            logging.error(f"Ошибка получения данных контракта: {e}")
            sys.exit(1)
        return contract_id, contract_data
    except Exception as e:
        logging.error(f"Ошибка компиляции контракта: {e}")
        sys.exit(1)

def generate_unique_token_name():
    """Генерирует уникальное имя токена."""
    unique_str = str(time.time()) + str(random.random())
    hash_str = hashlib.sha256(unique_str.encode()).hexdigest()
    return "Token_" + hash_str[:8], "TKN" + hash_str[:3]

def create_token(chain_name):
    """Создаёт токен в указанной сети."""
    try:
        handler = NetworkHandler(chain_name)
    except (Exception, NetworkHandlerError) as e:
        logging.error(f"{e}")
        return
    
    balance_wei = handler.get_balance()
    logging.info(f"Баланс: {handler.to_ether(balance_wei)} ETH")

    contract_id, contract_data = compile_contract(SOLIDITY_CODE)
    contract = handler.web3.eth.contract(abi=contract_data['abi'], bytecode=contract_data['bin'])
    token_name, token_symbol = generate_unique_token_name()
    initial_supply = handler.web3.to_wei(1000000, 'ether')

    try:
        gas_estimate = contract.constructor(token_name, token_symbol, initial_supply).estimate_gas({
            'from': handler.account_address
        })
        gas_limit = int(gas_estimate * 1.1)
        logging.info(f"Оценка газа: {gas_estimate}, Лимит газа: {gas_limit}")
    except Exception as e:
        logging.error(f"Ошибка оценки газа: {e}")
        return

    nonce = handler.web3.eth.get_transaction_count(handler.account_address)
    tx_params = handler.get_tx_params(gas_limit, nonce)
    if not tx_params:
        return

    tx = contract.constructor(token_name, token_symbol, initial_supply).build_transaction(tx_params)
    signed_tx = handler.web3.eth.account.sign_transaction(tx, handler.private_key)
    tx_hash = handler.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    logging.info(f"Транзакция отправлена: {tx_hash.hex()}")

    receipt = handler.web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        logging.info(f"Контракт развёрнут: {receipt.contractAddress}, блок: {receipt.blockNumber}")
    else:
        logging.warning("Транзакция провалилась")

def main(chain_list):
    for name in chain_list:
        create_token(name)


if __name__ == "__main__":
    logging.info("скрипт выполняется")
    chain_list = ['irys', 'eth_sepolia', 'monad', 'mega', 'somnia', 'rise', 'base_sepolia', 'moca', 'kite', 'incentiv', 'camp', 'pharos', '0g', 'sahara', 'nexus']
    #chain_list = ['moca', 'somnia']
    main(chain_list)
    logging.info("Скрипт завершён")