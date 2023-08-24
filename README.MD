# Ping Pong Bot
This bot is an event listener for a Ping Pong Smart contract. Every time an Ping event is emitted, the pong function of the Smart Contract is called passing the transaction hash of the ping event.

Requirements:
1. You will need to have a wallet with funds in the EVM compatible network that you want to run the bot.
2. Get the Private Key of that wallet.
3. A PingPong Contract, for example [0x7d3a625977bfd7445466439e60c495bdc2855367](https://goerli.etherscan.io/address/0x7d3a625977bfd7445466439e60c495bdc2855367)

To start the bot:
1. Create a virtual env with python3 -m venv .venv
2. activate the venv with: source .venv/bin/activate (Linux Users)
3. install the requirements with: pip install -r requirements.txt
4. create a .env file with the following values or change the .env.example file to .env and then complete the values:
 - RPC_HTTP_PROVIDER=https://goerli.infura.io/v3/<your-api-key>  <- you can defined whatever rpc http provider you have
 - PRIVATE_KEY=<the_private_key_of_the_bot>
5. Run the bot calling: python PingPong.py
 - You can change the fromBlock value to start the bot adding the parameter fromBlock in the initialization of the Bot at the end of the file

 TIP:
 For the RPC provider you can use some public RPCs, but should be chosen properly because not all the public RPCs has enabled the createFilter method.
 Infura or Alchemy can be used, but take a look into the amount of request that you are going to do :), the free tier could limit you.
 For goerli testnet, you can use the https://eth-goerli.g.alchemy.com/v2/demo RPC.