#! /bin/bash
# Install GOLANG

pushd $HOME
sudo rm -rf go1.20.2.linux-amd64.tar.gz
yes | wget https://go.dev/dl/go1.20.2.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.20.2.linux-amd64.tar.gz

export PATH=$PATH:/usr/local/go/bin
go version
go env GOROOT GOPATH

# Download and build BTCD
export GOPATH=$HOME/go
export GOROOT=/usr/local/go

git clone https://github.com/lightningnetwork/lnd.git || true
git clone https://github.com/btcsuite/btcd.git || true

cd $HOME/btcd
go install . ./cmd/... || true

cd $HOME/lnd
make install || true

popd
