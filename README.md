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

## Getting started

After you finished installation, you can start sarafan node with just:

```bash
sarafan
```

or you can execute python module:

```bash
python -m sarafan
```

Web UI will be available at http://127.0.0.1:21112 by default.

## Configuration

It is possible to configurate node multiple ways. 

* configuration file
* environment variable
* command line options

Environment will overwrite configuration file variables and command line options 
will overwrite them both.

`--api-port`, `SARAFAN_API_PORT`, `api_port` can be used to change rest api port (`21112` by default)

`--log-level`, `SARAFAN_LOG_LEVEL`, `log_level` minimal log level to output to console (default `ERROR`)
