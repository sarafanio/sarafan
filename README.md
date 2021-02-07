# Sarafan Node

Sarafan node is a service to access Sarafan content delivery network.

Features:

* upstream implementation
* web interface to read and publish content
* Kademlia-like content discovery
* all communication is hidden in tor overlay
* strict and safe distributed content bundle format
* direct ethereum connection (TODO)
* direct tor network connection (TODO)

## Install

### From pip

```bash
pip install sarafan
```

## Running tor proxy

### MacOS

```bash
brew install tor
cp /usr/local/etc/tor/torrc{.sample,}
sed -i '' 's/#ControlPort 9051/ControlPort 9051/g' /usr/local/etc/tor/torrc
brew services start tor
```

## Starting ethereum node

For development, you likely have to spin up your own blockchain and contract. 
The easiest possible option is to use Ganache https://www.trufflesuite.com/ganache
to start blockchain with your own node.

Start Ganache app and create a new blockchain.

You should also deploy contract. See contract repository README
for details: https://github.com/sarafanio/contract#development

## Getting started

After you finished installation, you can start sarafan node with just:

```bash
sarafan
```

or you can execute python module:

```bash
python -m sarafan
```

Web UI will be available at http://127.0.0.1:9231 by default.

## Configuration

It is possible to configurate node multiple ways. 

* configuration file
* environment variable
* command line options

Environment will overwrite configuration file variables and command line options 
will overwrite them both.

`--api-port`, `SARAFAN_API_PORT`, `api_port` can be used to change rest api port (`21112` by default)

`--log-level`, `SARAFAN_LOG_LEVEL`, `log_level` minimal log level to output to console (default `ERROR`)

## Charging test account

Example `truffle console` session:

```javascript
let token = await SarafanToken.deployed();
let content = await SarafanContent.deployed();
let accounts = await web3.eth.getAccounts();
// transfer tokens to the second account
await token.transfer(accounts[1], 1000);
// approve spending for content contract from the second account
await token.approve(content.address, 1000, {from: accounts[1]});
```
