#! /bin/bash

FETCHED=$PROJ_HOME/lnrpc/foreign

mkdir -p $FETCHED

curl -o lightning.proto -s https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/lightning.proto || true
python -m grpc_tools.protoc --proto_path=$PROJ_HOME/third_party/googleapis:. --python_out=. --grpc_python_out=. lightning.proto

curl -o router.proto -s https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/routerrpc/router.proto || true
python -m grpc_tools.protoc --proto_path=$PROJ_HOME/third_party/googleapis:. --python_out=. --grpc_python_out=. router.proto

curl -o walletunlocker.proto -s https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/walletunlocker.proto || true
python -m grpc_tools.protoc --proto_path=$PROJ_HOME/third_party/googleapis:. --python_out=. --grpc_python_out=. walletunlocker.proto
