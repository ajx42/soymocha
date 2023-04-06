import logging
import paramiko
import sys
import os
import subprocess as sp
from smparser import parse_manifest
from smutils import consts, smfiles, get_connections
from argparse import ArgumentParser
import yaml
import time


def create_node_targets(filename):
    with open(filename, 'r') as f:
        data = yaml.safe_load(f)

    # Access the nodes and the channels data
    nodes = data.get('Nodes')
    channels = data.get('Channels')
    node_dict = {}
    for channel in channels.values():
        second_node = channel['secondNode']
        first_node_name = channel['firstNode']
        first_node = nodes[first_node_name]
        local_amt = channel['localAmt']
        node_dict[second_node] = {
            'target': first_node_name,
            'ip': first_node['ip'],
            'identity_pubkey': first_node['identity_pubkey'],
            'local_amt': local_amt,
            'name': first_node['name']
        }
        mining_node = nodes['mining_node']['name']
    return node_dict, mining_node


def create_channels(details, pkey, filename='routing.yaml'):
    node_dict, mining_node = create_node_targets(filename)

    # for each node in the manifest, connect to it and create channels.
    # to connect to node1 <-> node2 we run the command at node2

    logging.info(
        "The following nodes are where we are creating the payment channels: {}".format(node_dict.keys()))

    for node, client in zip(details, get_connections(details, pkey)):
        # only connect to nodes that are in the keys in node_dict, i.e. the second member in the p2p channel
        if node.name not in node_dict.keys():
            continue

        # start an interactive shell sesssion, so we can run multiple commands
        shell = client.invoke_shell()
        while not shell.recv_ready():
            time.sleep(0.1)
        shell.recv(1024).decode()  # Clear the initial login message

        shell.send("source mocha/assets/lightning/lndprofile.sh")
        shell.send("source mocha/assets/lndconfgen_done.sh")

        logging.info("Connecting to node: {}".format(node.name))
        shell.send("lncli-ws connect {}@{}".format(
            node_dict[node.name]['identity_pubkey'], node_dict[node.name]['ip']))
        output = shell.recv(4096)  # Receive the output from the command
        # print(output.decode())  # Print the output as a string
        logging.info(
            "Confirmed connection between {} <---> {}".format(node.name, node_dict[node.name]['name']))

        shell.send("lncli-ws openchannel --node_key={} --local_amt={}".format(
            node_dict[node.name]['identity_pubkey'], node_dict[node.name]['local_amt']))
        output = shell.recv(4096)  # Receive the output from the command
        # print(output.decode())  # Print the output as a string
        logging.info(
            "Payment channel is pending with amount {} committed".format(node_dict[node.name]['local_amt']))

        logging.info(
            "You will need to mine 6 blocks to confirm the payment channels. Please do so on your mining node: {}.".format(mining_node))


def disconnect_channels(details, pkey, filename='routing.yaml'):
    node_dict, mining_node = create_node_targets(filename)
    for node, client in zip(details, get_connections(details, pkey)):
        # only connect to nodes that are in the keys in node_dict, i.e. the second member in the p2p channel
        if node.name not in node_dict.keys():
            continue

        # start an interactive shell sesssion, so we can run multiple commands
        shell = client.invoke_shell()
        while not shell.recv_ready():
            time.sleep(0.1)
        shell.recv(1024).decode()  # Clear the initial login message

        shell.send("source mocha/assets/lightning/lndprofile.sh")
        shell.send("source mocha/assets/lndconfgen_done.sh")

        shell.send("lncli-ws disconnect {} force".format(
            node_dict[node.name]['identity_pubkey']))  # using force will disconnect even with an active channel
        logging.info("Disconnected from node: {}".format(
            node_dict[node.name]["name"]))
        shell.recv(4096)  # Receive the output from the command


def main():
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()
    parser.add_argument("--manifest", help="manifest for cloudlab")
    parser.add_argument("--pvt-key", help="private key (file)")
    parser.add_argument("--session", help="unique session id")
    parser.add_argument(
        "--disconnect", help="disconnect all channels you have defined in the yaml file")

    parser.add_argument(
        "--config", help="yaml file with channels and nodes defined")

    args = parser.parse_args()

    pkey = paramiko.Ed25519Key.from_private_key_file(args.pvt_key)

    details = parse_manifest(args.manifest)

    if args.disconnect:
        disconnect_channels(details, pkey, args.config)
        sys.exit(0)

    if args.config:
        create_channels(details, pkey, args.config)


if __name__ == '__main__':
    main()

# python smchannels.py --manifest manifest.xml --pvt-key ~/.ssh/id_ed25519 --session mocha --config routing.yaml
