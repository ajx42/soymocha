# pysoymocha
### Bunch of tools to help with setup

## Cloudlab
Generate a TMUX script under `$PROJ_HOME/build`: `tmux.<session_name>.sh`.
```bash
# Local
python sminstaller.py --manifest manifest.xml --pvt-key ~/.ssh/id_ed25519 --session mocha
``` 

Run this script to build out a tmux session. Then attach the session to get started. This should have zsh installed on all nodes, so type in `zsh` if the logon doesn't directly launch the zsh prompt.

## Lightning Network
This requires some manual intervention. I'll try to fully automate the process soon.

### Getting the config files on Cloudlab nodes

Use the `--app` option to pass lightning and `--clear` to clear out any already existing lightning configuration.

```bash
# Local
python sminstaller.py --manifest manifest.xml --pvt-key ~/.ssh/id_ed25519 --session mocha --app lightning --clear
```

The below will copy over `assets/lightning` to all remote nodes under the directory: `<session_name>/assets/lightning`.
```bash
# Local
python sminstaller.py --manifest manifest.xml --pvt-key ~/.ssh/id_ed25519 --session mocha --app lightning
```

### Running BTC nodes (simnet) using BTCD

On nodes that are going to run `btcd`, generate btc config. Let this node be `nodeX`.
```bash
# Cloudlab Node
source <session_name>/assets/lightning/btcconfgen.sh
cd go/bin
./btcd
```

### Running Lightning Nodes using LND

Use the following to copy over RPC certificate and LND configuration to the other nodes (that will be LND nodes).

```bash
# Local
python smlightning.py --manifest ../manifest.xml --pvt-key ~/.ssh/id_ed25519 --session <session_name> --config "nodeX:*" 
```
The above will produce the `<session_name>/assets/lndconfgen_done.sh`. On the LND nodes: 
```bash
# Cloudlab Node
source <session_name>/assets/lndconfgen_done.sh
source <session_name>/assets/lightning/lndprofile.sh
lnd-ws
```

While LND is running, on each of these nodes use `lncli-ws` to create a wallet or unlock it if it already exists. (This will need a separate terminal, since we need to keep LND running while we do this.)

```bash
# Cloudlab Node
lncli-ws create
```

### Funding Wallets

To fund the wallet, we can use the BTC node(s) to mine and direct the funds to these wallets.
On the LND node, whose wallet we want to fund, generate a new address:

```bash
# Cloudlab Node
lncli-ws newaddress np2wkh

# Output
{
    "address": "some long hex string"
}
```

On corresponding BTC node, stop `btcd`, and restart as follows:
```bash
# Cloudlab Node
btcd --miningaddr=<the address we got in previous step>
```
On another terminal, on the same node:
```bash
# Cloudlab Node
btcctl generate 100
```
This will generate 100 blocks and add the mined BTC to the specified wallet.

Similarly fund other wallets on other nodes.

### Opening a channel
There are 3 steps to this process. 
1. We connect the nodes that we want a channel in between.
2. We create a channel between these nodes which will remain pending till the commited transactions reach a specific depth. 
3. We mine a few blocks so that the said depth is reached and the channel is confirmed.

Initially these will return empty lists:
```bash
# Cloudlab LND Node
lncli-ws listpeers
lncli-ws pendingchannels
lncli-ws listchannels
```

Use `getinfo` to get public identity of a node:
```bash
# On Cloudlab LND Node A 
lncli-ws getinfo
hostname -I
```

Then use this address on another node to connect the two:
```bash
# On Cloudlab LND Node B
lncli-ws connect <address_of_A>@<ip_of_A>
```
Now we should see something upon running this:
```bash
# Cloudlab Node A or B
lncli-ws listpeers
```
Open a channel as follows:
```bash
lncli-ws openchannel --node_key=<address_of_A> --local_amt=1000000

# Expected Output
{
  "funding_txid": "7eeabff3aea0cf4d64e2823841f045e8d3a33cceff237183e3807afe5df2dfa5"
}
```

This channel should get listed in `lncli-ws pendingchannels`.
Mine 6 blocks to confirm this channel: `lncli-ws generate 6`.
We should be able to see the channel in: `lncli-ws listchannels` now.

### Sending a payment
First, we need to add an invoice on the recipient, which the sending node will use to trigger payments.
```bash
# Cloudlab Node A
lncli-ws addinvoice --amt=10000

# Expected Outputs
{
  "r_hash": "a9b22eca10de08426f11f3f59b8a733f1af831a699c1b3f6ca632533239dc1dd",
  "pay_req": "lnsb1pd8pxdzpp54xezajssmcyyymc3706ehznn8ud0svdxn8qm8ak2vvjnxguac8wsdqqcqzyse0qkh2fdn4adwlz598s4v9l2ulner3jalncsjf33za0r3hksv2u3m7vw2663ypaqcc4fjsuzeh5n5hfsqyggwk3rzp6neng4hza8stgp4aaszp"
}
```

And now, on the sending node:
```bash
# Cloudlab Node B
lncli-ws payinvoice <pay_req>
```

Upon successful execution, we will see the fund change reflected in the channel info.