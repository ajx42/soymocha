#! /bin/bash

mkdir -p ~/.lnd;
cat > ~/.lnd/lnd.conf << EOL
bitcoin.active=1
bitcoin.simnet=true
bitcoin.node=btcd
btcd.rpchost=%%HOST%%
btcd.rpcuser=%%USER%%
btcd.rpcpass=%%PASS%%
btcd.rpccert=$HOME/.btcd/rpc.cert
debuglevel=debug
EOL

