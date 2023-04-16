# fetch authorisation related files from remote nodes
# for RPC purposes

import grpc
import sys
import os
import logging
import csv
import subprocess as sp

from argparse import ArgumentParser
from py.smparser import parse_manifest
from connector import LNConnector, FILESTORE, PASSWORD, getRPCListenSocket, \
        BTCConnector, getGraph, getConnectors

import lightning_pb2 as ln
import lightning_pb2_grpc as lnrpc
import walletunlocker_pb2 as wu
import walletunlocker_pb2_grpc as wurpc

# Due to updated ECDSA generated tls.cert we need to let gprc know that
# we need to use that cipher suite otherwise there will be a handhsake
# error when we communicate with the lnd rpc server.
os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

def fetchfile(fileloc, node, outloc):
    scp_cmd = 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r {}@{}:{} {}'.format(
        node.username, node.hostname,
        fileloc, outloc
    )
    logging.info(scp_cmd)
    try:
        sp.check_call(scp_cmd, shell=True, timeout=10)
    except:
        logging.warning("Could not fetch {} from {}".format(fileloc, node.name))

def fetchAllNodes(details):
    for nodedetail in details:
        outloc = '{}/{}/'.format(FILESTORE, nodedetail.name)
        os.makedirs(outloc, exist_ok=True)
        fetchfile('.lnd/tls.cert', nodedetail, outloc)
        fetchfile('.lnd/lnd.conf', nodedetail, outloc)
        fetchfile('.lnd/data/chain/bitcoin/simnet/*.macaroon', nodedetail, outloc)
        fetchfile('.btcd/rpc.cert', nodedetail, outloc)
        fetchfile('.btcd/rpc.key', nodedetail, outloc)

def unlockOrCreate(name):
    cert = open(os.path.expanduser('{}/{}/tls.cert'.format(FILESTORE, name)), 'rb').read()
    creds = grpc.ssl_channel_credentials(cert)
    channel = grpc.secure_channel(getRPCListenSocket(name), creds)
    wu_stub = wurpc.WalletUnlockerStub(channel)
    try: 
        resp = wu_stub.GenSeed(wu.GenSeedRequest())
        mnemonic = ' '.join(resp.cipher_seed_mnemonic)
        logging.info("Attempting to create wallet on: {}".format(name))
        req = wu.InitWalletRequest(
            wallet_password=PASSWORD,
            cipher_seed_mnemonic=resp.cipher_seed_mnemonic )
        initresp = wu_stub.InitWallet(req).admin_macaroon
        logging.info("Wallet Create: success")
        return
    except:
        logging.warning("Wallet Create: failed")

    try:
        logging.info("Attempting to unlock wallet on: {}".format(name))
        req = wu.UnlockWalletRequest()
        req.wallet_password = PASSWORD
        wu_stub.UnlockWallet(req)
        logging.info("Wallet Unlock: success")
    except:
        logging.warning("Wallet Unlock: failed")
    return None

def unlockOrCreateAllNodes(details, excludes=None):
    for node in details:
        if node.name not in excludes:
            unlockOrCreate(node.name)

def getInfo(name):
    conn = LNConnector(name)
    return conn.getinfo()

def getInfoAllNodes(details, excludes=None):
    for node in details:
        if node.name not in excludes:
            print(getInfo(node.name).identity_pubkey)

def genFundAllNodes(details, excludes, filename):
    with open(filename, 'w+') as rf:
        for node in details:
            if node.name not in excludes:
                conn = LNConnector(node.name)
                rf.write('pkill -f btcd\n')
                rf.write('sleep 3\n')
                rf.write('./go/bin/btcd --miningaddr {} &\n'.format(conn.getAddress()))
                rf.write('sleep 5\n')
                rf.write('./go/bin/btcctl generate 50\n')
                rf.write('sleep 10\n')


def testBTCAllNodes(details, excludes):
    for node in details:
        if node.name not in excludes:
            x = BTCConnector(node.name)
            x.setMiningAddress()

def buildChannelGraph(details, excludes, graphfile):
    conns = getConnectors(details, excludes)
    edges = getGraph(graphfile)
    for e in edges:
        conns[e.src].connectPeer(conns[e.dst])
        conns[e.src].addChannel(conns[e.dst], e.val)

def commitChannels(details, excludes):
    for node in details:
        if node.name not in excludes:
            btcc = BTCConnector(node.name)
            btcc.generateBlocks(7)
            return

def printActiveChannels(details, excludes):
    for node in details:
        if node.name not in excludes:
            conn = LNConnector(node.name)
            print(conn.getActiveChannels())

def disconnectAllChannels(details, excludes):
    for node in details:
        if node.name not in excludes:
            conn = LNConnector(node.name)
            conn.closeActiveChannels()

def disconnectChannelGraph(details, excludes, graphfile):
    disconnectAllChannels(details, excludes)
    conns = getConnectors(details, excludes)
    edges = getGraph(graphfile)
    for e in edges:
        try:
            conns[e.src].disconnectPeer(conns[e.dst])
        except:
            pass

def main():
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()
    parser.add_argument("--manifest", help="manifest for cloudlab")
    parser.add_argument("--op", help="operation")
    parser.add_argument("--exclude", help="exclude op on these nodes: nodeX,nodeY,..")
    parser.add_argument("--file", help="file as needed by operation")
    args = parser.parse_args()
    details = parse_manifest(args.manifest)

    with open('{}/config.csv'.format(FILESTORE), 'w+') as wf:
        writer = csv.DictWriter(wf, fieldnames=list(details[0]._asdict().keys()))
        writer.writeheader()
        for entry in details:
            writer.writerow(entry._asdict())

    excludes = args.exclude.split(',') if args.exclude else []

    if args.op == "fetch":
        fetchAllNodes(details)
    elif args.op == "initwallet":
        unlockOrCreateAllNodes(details, excludes)
    elif args.op == "test":
        getInfoAllNodes(details, excludes)
    elif args.op == "generatefundscript":
        genFundAllNodes(details, excludes, args.file)
    elif args.op == "testbtc":
        testBTCAllNodes(details, excludes)
    elif args.op == "buildgraph":
        buildChannelGraph(details, excludes, args.file)
    elif args.op == "disconnectgraph":
        disconnectChannelGraph(details, excludes, args.file)
    elif args.op == "commit":
        commitChannels(details, excludes)
    elif args.op == "printchannels":
        printActiveChannels(details, excludes)

if __name__ == '__main__':
    main()
