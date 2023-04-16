#! /bin/bash

mkdir -p ~/.lnd;
cat > ~/.lnd/lnd.conf << EOL
bitcoin.active=1
bitcoin.simnet=true
bitcoin.node=btcd
rpclisten=127.0.0.1:10009
rpclisten=$(host=($(hostname -I)); echo "${host[1]}:8080")
btcd.rpchost=%%HOST%%
btcd.rpcuser=%%USER%%
btcd.rpcpass=%%PASS%%
btcd.rpccert=$HOME/.btcd/rpc.cert
debuglevel=debug
EOL

