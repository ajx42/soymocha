import grpc
import sys
import os
import logging
import csv
import subprocess as sp
import codecs
import requests
import json
import ssl

from collections import namedtuple
from argparse import ArgumentParser
from py.smparser import parse_manifest

import lightning_pb2 as ln
import lightning_pb2_grpc as lnrpc
import walletunlocker_pb2 as wu
import walletunlocker_pb2_grpc as wurpc

FILESTORE = '{}/lnrpc/foreign/'.format(os.environ['PROJ_HOME'])
PASSWORD = str.encode("12345678")

Edge = namedtuple('Edge', ['src', 'dst', 'val'])

def getField(field, file):
    ret = []
    with open(file, 'r') as rf:
        for line in rf:
            if line.strip().startswith(field):
                ret.append(line.strip().split('=')[1])
    return ret

def getRPCListenSocket(name):
    vals = getField('rpclisten=', '{}/{}/lnd.conf'.format(FILESTORE, name))
    for v in vals:
        # ignore localhost
        if not v.startswith('127.0.0.1'):
            return v
    return None

def getConnectors(details, excludes):
    conns = []
    for node in details:
        if node.name in excludes:
            conns.append(None)
        else:
            conns.append(LNConnector(node.name))
    return conns

def getGraph(graphFile):
    graph = []
    with open(graphFile, 'r+') as gf:
        for line in gf:
            if line.strip().startswith('edge'):
                src, dst, val = (int(x.strip()) for x in line.strip().split('=')[1].split(','))
                graph.append(Edge(src, dst, val))
    return graph

class LNConnector:
    def __init__(self, name):
        logging.basicConfig(level=logging.INFO)

        self.name = name
        self.cert = open(os.path.expanduser('{}/{}/tls.cert'.format(FILESTORE, name)), 'rb').read()
        self.creds = grpc.ssl_channel_credentials(self.cert)
        self.socketstr = getRPCListenSocket(name)
        self.ipstr = self.socketstr.split(':')[0]
        self.channel = grpc.secure_channel(self.socketstr, self.creds)
        self.stub = lnrpc.LightningStub(self.channel)
            # try to read from files
        with open(os.path.expanduser('{}/{}/admin.macaroon'.format(FILESTORE, name)), 'rb') as f:
            macaroon_bytes = f.read()
            self.macaroon = codecs.encode(macaroon_bytes, 'hex')

        self.address = None

    def getinfo(self):
        return self.stub.GetInfo(ln.GetInfoRequest(), metadata=[('macaroon', self.macaroon)])

    def getNewAddress(self):
        address_req = ln.NewAddressRequest(type=ln.NESTED_PUBKEY_HASH)
        resp = self.stub.NewAddress(address_req, metadata=[('macaroon', self.macaroon)])
        logging.info("Generated New P2PKH Address for {}: {}".format(self.name, resp.address))
        self.address = resp.address
        return resp.address

    def getAddress(self):
        if self.address == None:
            return self.getNewAddress()
        else:
            return self.address

    def connectPeer(self, otherConn):
        otherAddr = otherConn.getinfo().identity_pubkey
        logging.info('Attempting to connect {} <> {}'.format(self.ipstr, otherConn.ipstr))
        lnaddr = ln.LightningAddress(pubkey=otherAddr, host=otherConn.ipstr)
        req = ln.ConnectPeerRequest(addr=lnaddr, timeout=10)
        self.stub.ConnectPeer(req, metadata=[('macaroon', self.macaroon)])

    def disconnectPeer(self, otherConn):
        otherAddr = otherConn.getinfo().identity_pubkey
        req = ln.DisconnectPeerRequest(pub_key=otherAddr)
        self.stub.DisconnectPeer(req, metadata=[('macaroon', self.macaroon)])

    def addChannel(self, otherConn, localAmount):
        otherAddr = otherConn.getinfo().identity_pubkey
        logging.info("Opening channel with: {}".format(otherAddr))
        req = ln.OpenChannelRequest(node_pubkey=bytes.fromhex(otherAddr), local_funding_amount=localAmount, target_conf=6)
        self.stub.OpenChannel(req, metadata=[('macaroon', self.macaroon)])

    def getActiveChannels(self):
        req = ln.ListChannelsRequest(
            active_only=True )
        return self.stub.ListChannels(req, metadata=[('macaroon', self.macaroon)]).channels

    def getPendingChannels(self):
        return self.stub.PendingChannels(
            ln.PendingChannelsRequest(), metadata=[('macaroon', self.macaroon)]).pending_open_channels

    def closeChannel(self, channel_pt):
        logging.info("Closing channel: {}".format(channel_pt))
        req = ln.CloseChannelRequest()
        req.channel_point.funding_txid_str = channel_pt.split(':')[0]
        req.channel_point.output_index = int(channel_pt.split(':')[1])
        req.force = True
        req.target_conf = 6
        resp = self.stub.CloseChannel(req, metadata=[('macaroon', self.macaroon)])

    def closeActiveChannels(self):
        channels = self.getActiveChannels()
        for channel in channels:
            self.closeChannel(channel.channel_point)

    def __del__(self):
        self.channel.close()

class BTCConnector:
    def __init__(self, name):
        self.name = name
        self.rpchost = getField('btcd.rpchost', '{}/{}/lnd.conf'.format(FILESTORE, name))[0]
        self.rpcuser = getField('btcd.rpcuser', '{}/{}/lnd.conf'.format(FILESTORE, name))[0]
        self.rpcpass = getField('btcd.rpcpass', '{}/{}/lnd.conf'.format(FILESTORE, name))[0]
        self.url = "https://{}:{}@{}".format(self.rpcuser, self.rpcpass, self.rpchost)
        self.cert_file = '{}/{}/rpc.cert'.format(FILESTORE, name)
        
        self.cmd_prefix = '{}/build/bin/btcctl --rpcuser={} --rpcpass={} --rpcserver={} --rpccert={} --simnet'.format(
                os.environ['PROJ_HOME'], self.rpcuser, self.rpcpass, self.rpchost, self.cert_file)

        self.lnconn = LNConnector(name)

    def setMiningAddress(self):
        addr = self.lnconn.getAddress()
        cmd_suffix = 'setgenerate false 0 "{}"'.format(addr)
        cmd = ' '.join([self.cmd_prefix, cmd_suffix])
        sp.check_output(cmd, shell=True)

    def generateBlocks(self, num):
        logging.info('Generating {} Blocks'.format(num))
        cmd_suffix = 'generate {}'.format(num)
        cmd = ' '.join([self.cmd_prefix, cmd_suffix])
        sp.check_output(cmd, shell=True)
