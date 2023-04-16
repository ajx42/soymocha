#! /bin/bash

# source this file!
echo 'n' | conda create --name mocha
conda activate mocha

conda install -c conda-forge paramiko

export PROJ_HOME=$(pwd)
export PYTHONPATH=$PYTHONPATH:$PROJ_HOME:$PROJ_HOME/python-bitcoinrpc/bitcoinrpc/

mkdir -p build
export GOPATH=$PROJ_HOME/build/
export GOROOT=/usr/local/go
cd $PROJ_HOME/third_party/btcd
go install . ./cmd/... || true
cd $PROJ_HOME
