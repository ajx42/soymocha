## Lightning Network RPC Connectivity in Python

This directory contains tools and libs to work with LN RPC.
It turns out LN RPC is the ideal way to do the kind of manipulation we are wanting to do in terms of setting up graphs and channels. Shells scripts are messy and require going back and forth between cloudlab and local. This work runs completely on our local end!

### Start
We assume that Lightning Network is already running on cloudlab. How? Using our other scripts in soymocha/py. But the wallets aren't unlocked/created. Neither are they funded. We also assume that project environment has been enabled, if you haven't done so, `source env.sh` in the project root dir.

### Step - 0: Preparation
```shell
# this will generate python RPC bindings for LNRPC services
./preproc.sh 

# fetch node configuration
python fetchauth.py --manifest ../manifest.xml --op fetch
```

### Step - 1: Create/Unlock wallets
Nodes on which LND is not running can be excluded as under.
```shell
python fetchauth.py --manifest ../manifest.xml --op initwallet --exclude node0
```

After the wallet is initialised, RPC servers get started on LND.

### Step - 2: Pull Config again
```shell
python fetchauth.py --manifest ../manifest.xml --op fetch
```

### Step - 3: Fund Wallets
This is the ugliest part. Since this requires RPC connection with BTCD which is missing features.
So, we will generate a funding script, and run it on cloudlab BTC node.

```shell
python fetchauth.py --manifest ../manifest.xml --op generatefundscript --exclude node0 --file target.sh
```
Run the `target.sh` script on CloudLab BTC node.

### Step 4: Prepare a graph.conf
A sample file is already provided. Each line has the format: `edge=<src>,<dst>,<local_amt>`
```shell
edge=2,3,20000
edge=2,4,20000
edge=3,5,20000
```

### Step 5: Build the graph
```shell
python fetchauth.py --manifest ../manifest.xml --op buildgraph --exclude node0 --file graph.conf

# generate a few blocks to commit the channels
python fetchauth.py --manifest ../manifest.xml --op commit --exclude node0
```

### Printing Channels
```shell
python fetchauth.py --manifest ../manifest.xml --op printchannels --exclude node0
```

### Disconnecting Graph
```shell
python fetchauth.py --manifest ../manifest.xml --op disconnectgraph --exclude node0 --file graph.conf
```

### Pending Channels
If your channels are not getting confirmed, the following can be the issue:
- Insufficient balance in the vertices.
- The chain length is less than 300. LND uses segwit data which is not enabled until minimum length of 300.
