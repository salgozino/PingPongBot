"""Class to handle the PingPong SC instance"""
import os
import json
import asyncio

from web3 import Web3, exceptions

from dotenv import load_dotenv
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
    filename='ping_pong_logs.log'
)

# Load environment variables
load_dotenv()


class Contract():
    # TODO: choose the proper RPC from the chainID
    web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_HTTP_PROVIDER")))

    def __init__(self, address, abi_path):
        # Just in case to prevent error.
        self.address = Web3.to_checksum_address(address.lower())
        self.abi_path = abi_path
        self.get_contract_from_abi()

    def get_abi(self):
        # TODO: Check if ABI is available.
        with open(self.abi_path, 'r') as abi_file:
            abi_data = json.load(abi_file)
            contract_abi = abi_data['abi']
        return contract_abi

    def get_contract_from_abi(self):
        # Load the ABI from the JSON file
        abi = self.get_abi()
        # Instantiate the smart contract
        self.contract = self.web3.eth.contract(
            address=self.address, abi=abi, decode_tuples=True)
        # TODO: raise error if contract was not possible to instantiate
        logging.info(f"Contract wit address {self.contract.address} attached")
        return self.contract

    def get_transaction(self, tx_hash: str):
        return self.web3.eth.get_transaction(tx_hash)

    def get_blocknumber_from_tx_hash(self, tx_hash: str):
        tx = self.get_transaction(tx_hash)
        if tx is not None:
            return tx['blockNumber']
        return None


class PingPongBot(Contract):

    def __init__(self, address, from_block: int = 9316725):
        super().__init__(address, os.path.join('abis', 'PingPong.json'))
        # get the chain id from the RPC configured
        self.chain_id = self.web3.eth.chain_id
        # Set default account as the BOT account from the Private Key stored as enviromental variable.
        self.bot_account = self.web3.eth.account.from_key(
            os.environ.get('PRIVATE_KEY', None))
        logging.info(
            f"The bot will be using the public address {self.bot_account.address}")
        # TODO: Add representative balance value for each chain
        self._check_enough_balance(0.00005)
        self.web3.eth.default_account = self.bot_account
        self.ping_filter = None
        self.pongs = set(self.get_all_pongs(from_block))
        start_block = self.get_last_ping_with_pong_blocknumber(from_block)
        if start_block is not None:
            self.from_block = start_block + 1
            # Need to update the ping filter to the new block.
            self._create_ping_filter(self.from_block)
        else:
            # No need to change the current ping filter because is the same block number
            # The ping_filter was created in get_last_ping_with_pong_blocknumber
            self.from_block = from_block

    def _check_enough_balance(self, min_balance=0.0005):
        balance = self.web3.eth.get_balance(self.bot_account.address)
        if balance < self.web3.to_wei(min_balance, 'ether'):
            raise ValueError(
                f"I only have {self.web3.from_wei(balance, 'ether')} in native token. "
                f"This is not enough. Please sendme some tips to {self.bot_account.address}"
                f" in chain {self.web3.eth.chain_id}"
            )

    def _check_if_ping_in_pongs(self, ping_hash: str):
        is_ping_in_pongs = False
        ping_hash = ping_hash.replace('0x', '')
        for pong in self.pongs:
            logging.debug(
                f"Checking ping with pong {pong['args']['txHash'].hex()[:6]}")
            if pong['args']['txHash'].hex() == ping_hash:
                logging.debug(f'Found a pong for the ping {ping_hash[0:6]}!')
                is_ping_in_pongs = True
                break
        return is_ping_in_pongs

    def _create_ping_filter(self, fromBlock):
        logging.info(f"Creating filter for ping event from block {fromBlock}")
        fromBlock = fromBlock if fromBlock == 'latest' else int(fromBlock)
        self.ping_filter = self.contract.events.Ping.create_filter(fromBlock=fromBlock)
        self.from_block = fromBlock
        return self.ping_filter

    def event_ping_filter(self, fromBlock='latest'):
        if self.ping_filter is None:
            self._create_ping_filter(fromBlock)
        else:
            logging.info("Using the same filter, because the block number hasn't changed")
        return self.ping_filter

    def event_ping_handler(self, event):
        logging.info(f"New ping event detected at block {event['blockNumber']}!. Doing pong")
        self.do_pong(event.transactionHash)
        self.from_block = event['blockNumber'] + 1
        self._create_ping_filter(self.from_block)
        return event

    def event_pong_filter(self, fromBlock='latest'):
        logging.info(f"Creating filter for pong event from block {fromBlock}")
        fromBlock = fromBlock if fromBlock == 'latest' else int(fromBlock)
        return self.contract.events.Pong.create_filter(fromBlock=fromBlock)

    def get_ping_from_pong(self, pong_event):
        ping_hash = pong_event['args']['txHash'].hex()
        return self.get_transaction(ping_hash)

    def get_all_pongs(self, fromBlock: int):
        """Get all the pong events starting in the fromBlock.
        fromBlock should be an integer.
        It will return a list with all the pong events. An empty list if no pongs events
        after the fromBlock"""
        return self.event_pong_filter(fromBlock).get_all_entries()

    def get_all_pings(self, fromBlock: int):
        """Get all the ping events starting in the fromBlock.
        fromBlock should be an integer.
        It will return a list with all the ping events. An empty list if no pongs events
        after the fromBlock"""
        return self.event_ping_filter(fromBlock).get_all_entries()

    def get_last_ping_with_pong_blocknumber(self, fromBlock=9316725):
        """Get the last pong emmited and return the ping block number of that pong"""
        pings = self.get_all_pings(fromBlock)
        pings_with_pongs = []
        if len(pings) > 0:
            for ping in pings:
                logging.debug(
                    f"Looking pong for the ping {ping['transactionHash'].hex()[2:8]}")
                if self._check_if_ping_in_pongs(ping['transactionHash'].hex()):
                    pings_with_pongs.append(ping)
        if len(pings_with_pongs) > 0:
            pings_with_pongs = sorted(
                pings_with_pongs, key=lambda d: d['blockNumber'], reverse=True)
            ping = pings_with_pongs[0]
            logging.info(
                f"The last ping that has a pong was on the block number {ping['blockNumber']}")
            return ping['blockNumber']
        return None

    def get_first_ping_blocknumber_without_pong(self, fromBlock=9316725):
        logging.info(
            f"Checking the first ping block number without a pong after block {fromBlock}")
        start_block = self.get_last_ping_with_pong_blocknumber(fromBlock)
        if start_block is not None:
            start_block += 1
            missed_pings = self.get_all_pings(start_block)
            if len(missed_pings) > 0:
                missed_pings = sorted(
                    missed_pings, key=lambda d: d['blockNumber'], reverse=False)
                start_block = missed_pings[0]['blockNumber']
        logging.info(f"The starting block should be {start_block}")
        return start_block

    def get_pinger(self):
        return self.contract.functions.pinger().call({'from': self.bot_account.address})

    def do_ping(self, number_of_pings=1):
        pinger = self.get_pinger()
        if pinger != self.bot_account.address:
            logging.error("The bot is not the pinger, can't do pings")
            return
        nonce = self.web3.eth.get_transaction_count(self.bot_account.address)
        tx_hashs = []
        logging.info(f"Starting to do {number_of_pings} pings")
        for i in range(number_of_pings):
            tx = self.contract.functions.ping().build_transaction({
                'chainId': self.chain_id,
                'nonce': nonce + i,
                # get_transaction_count doesn't count the pending txs, then the pendings will be replaced
                'gasPrice': self.web3.eth.gas_price,
                'from': self.bot_account.address
            })
            # Sign the transaction
            signed_transaction = self.bot_account.sign_transaction(tx)
            try:
                tx_hash = self.web3.eth.send_raw_transaction(
                    signed_transaction.rawTransaction)
            except ValueError as e:
                message = e.args[0]['message']
                if 'insufficient funds for gas' in message:
                    raise ValueError(
                        'Not enought funds to do a ping!. Closing the bot. Please send me money and restart me!')
                else:
                    # TODO: Catch other errors within ValueError
                    raise ValueError(e)
            except Exception as e:
                logging.error(
                    f"Error while sending raw txs for ping. {tx_hash.hex()}")
                logging.error(e)
                break
            tx_hashs.append(tx_hash)

        receipts = []
        for tx_hash in tx_hashs:
            while True:
                try:
                    self.web3.eth.wait_for_transaction_receipt(tx_hash)
                    receipts.append(
                        self.web3.eth.get_transaction_receipt(tx_hash))
                    logging.info(
                        f"Ping executed with tx hash {tx_hash.hex()[:6]}")
                    break
                except exceptions.TimeExhausted:
                    # keep waiting!
                    logging.info(
                        f"Waiting for more time to the ping tx {tx_hash.hex()[:6]} be minted")
                    pass
                except Exception as e:
                    logging.error(
                        f"Error while waiting for ping tx to be mined. {tx_hash.hex()}")
                    logging.error(e)
                    break

    def do_pong_on_missing_pings(self):
        logging.info(f"Checking missed pings since block {self.from_block}")
        # from_block was already defined in __init__ as the block where the first
        # missed ping is.
        for ping in self.event_ping_filter(self.from_block).get_all_entries():
            event = self.event_ping_handler(ping)
            self.from_block = event['blockNumber'] + 1
        logging.info(f"I'm up to date to the block {self.from_block}")
        return self.from_block

    def do_pong(self, ping_hash: bytes):
        logging.info(f"Calling pong with the ping tx hash {ping_hash.hex()}")
        if not self._check_if_ping_in_pongs(ping_hash.hex()):
            tx = self.contract.functions.pong(ping_hash.hex()).build_transaction({
                'chainId': self.chain_id,
                'nonce': self.web3.eth.get_transaction_count(self.bot_account.address),
                # get_transaction_count doesn't count the pending txs, then the pendings will be replaced
                'gasPrice': self.web3.eth.gas_price
            })
            # Sign the transaction
            signed_transaction = self.bot_account.sign_transaction(tx)
            while True:
                try:
                    # Send the transaction
                    tx_hash = self.web3.eth.send_raw_transaction(
                        signed_transaction.rawTransaction)
                    logging.debug(
                        "Transaction Hash for the pong function call:", tx_hash.hex())
                    self.web3.eth.wait_for_transaction_receipt(
                        tx_hash)
                    receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                    logging.info(
                        f'Receipt received with tx hash {receipt.transactionHash.hex()} at block {receipt.blockNumber}')
                    return receipt
                except exceptions.TimeExhausted:
                    # Increase the gas price as the next step of the current gas price.
                    tx, tx_hash = self.speed_tx(tx, tx_hash)
                except ValueError as e:
                    message = e.args[0]['message']
                    if 'insufficient funds for gas' in message:
                        raise ValueError(
                            'Not enought funds to do a pong!. Closing the bot." \
                            " Please send me money and then restart me!'
                        )
                    else:
                        # TODO: Catch other errors within ValueError
                        raise ValueError(e)
        else:
            logging.error(
                f"The ping with hash {ping_hash.hex()[2:8]} already has pong, should be in this function")
            return None

    def speed_tx(self, tx, tx_hash):
        new_gas_price = int(self.web3.eth.gas_price * 1.125)
        if new_gas_price > tx['gasPrice']:
            tx['gasPrice'] = new_gas_price
            logging.info(
                f"Gas is low, tx send again with gasPrice increased to {tx['gasPrice']}."
            )
            signed_transaction = self.bot_account.sign_transaction(
                tx)
            # Send the transaction
            tx_hash = self.web3.eth.send_raw_transaction(
                signed_transaction.rawTransaction)
            logging.info(
                f"New tx hash starts with {tx_hash.hex()[:6]}")
        else:
            logging.info("I will wait once again without modifying the gasPrice because new gasPrice"
                         " is lower than current gasPrice")
        return tx, tx_hash

    async def loop_ping_listener(self, poll_interval=5):
        logging.info(
            f"Now I will ben listening for every new ping event emitted after block {self.from_block} and do a pong.")
        while True:
            pings = None
            try:
                pings = self.event_ping_filter(self.from_block).get_all_entries()
            except Exception as e:
                logging.error('Error trying to get all ping events.')
                logging.error(e)
                # Reset the ping filter
                self.ping_filter = None
            if pings:
                try:
                    for ping in pings:
                        self.event_ping_handler(ping)
                except ValueError:
                    # not enough funds for example
                    break
                except Exception as e:
                    logging.error('Error trying to handle a ping event')
                    logging.error(e)
            await asyncio.sleep(poll_interval)

    def run(self):
        # Get the old events due to bot broken.
        self.do_pong_on_missing_pings()
        # Create an async loop to start listening new events
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                asyncio.gather(
                    self.loop_ping_listener(),
                    return_exceptions=True
                )
            )
        except KeyboardInterrupt:
            logging.info("Hasta la vista, baby!")
        finally:
            # close loop to free up system resources
            loop.close()


if __name__ == "__main__":
    bot = PingPongBot(
        address='0x7d3a625977bfd7445466439e60c495bdc2855367')  # Same SC deployed to test with pings
    bot.run()
