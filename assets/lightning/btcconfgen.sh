#! /bin/bash
mkdir -p $HOME/.btcd;
rm -f $HOME/.btcd/btcd.conf
cat > $HOME/.btcd/btcd.conf << EOL
simnet=1
txindex=1
rpclisten=127.0.0.1
rpclisten=$(host=($(hostname -I)); echo ${host[0]})
rpcuser=$(date '+%s%N-ln-workshop' | sha256sum | head -c 20)
rpcpass=$(date '+%s%N-ln-workshop' | sha256sum | head -c 32)
rpclimituser=$(date '+%s%N-ln-workshop' | sha256sum | head -c 20)
rpclimitpass=$(date '+%s%N-ln-workshop' | sha256sum | head -c 32)
rpcmaxclients=100
rpcmaxwebsockets=300
debuglevel=debug
EOL

mkdir -p $HOME/.btcctl;
rm -f $HOME/.btcctl/btcctl.conf
cat > $HOME/.btcctl/btcctl.conf << EOL
simnet=1
$(cat ~/.btcd/btcd.conf | grep rpcuser=)
$(cat ~/.btcd/btcd.conf | grep rpcpass=)
EOL

