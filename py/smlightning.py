import os
import logging
import sys
import paramiko
import subprocess as sp

from smparser import parse_manifest
from smutils import consts, smfiles, get_connections
from argparse import ArgumentParser

def preproc_source_targets(source, targets, details):
    node_names = {x.name for x in details}
    if source not in node_names:
        logging.error("Unknown Source Node for RPC Certificate Tx: {}".format(source))
        return
    targets = set(targets).difference({source})
    if "*" in targets:
        targets = node_names.difference({source})
    elif targets.intersection(node_names) != targets:
        logging.error("Unknown Target Nodes for RPC Certificate Tx: {}".format(targets))
        return
    return source, targets

def copy_btc_node(details, pkey, source, targets):
    source, targets = preproc_source_targets(source, targets, details)
    
    if not source or not targets:
        return

    source_node = None
    for node in details:
        if node.name == source:
            source_node = node

    for node, client in zip(details, get_connections(details, pkey)):
        if node.name not in targets:
            continue
    
        client.exec_command("mkdir -p .btcd")

        scp_cmd = 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r {}@{}:{} {}@{}:{}'.format(
            source_node.username, source_node.hostname,
            ".btcd/rpc.cert",
            node.username, node.hostname,
            ".btcd/rpc.cert"
        )

        sp.check_call(scp_cmd, shell=True)

def update_configurations(details, pkey, session, source, targets):
    source, targets = preproc_source_targets(source, targets, details)

    if not source or not targets:
        return

    tmpfile = os.path.join('/tmp', '_'.join(['btcdconf', source]))

    source_node = None
    for node in details:
        if node.name == source:
            source_node = node

    scp_cmd = 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r {}@{}:{} {}'.format(
        source_node.username, source_node.hostname,
        ".btcd/btcd.conf", tmpfile)

    sp.check_call(scp_cmd, shell=True)

    host = None
    user = None
    pwd  = None

    with open(tmpfile, 'r') as tf:
        for line in tf:
            if 'rpcuser' in line:
                user = line.strip().split('=')[1]
            if 'rpclisten' in line:
                host = line.strip().split('=')[1]
            if 'rpcpass' in line:
                pwd = line.strip().split('=')[1]

    if not host or not user or not pwd:
        logging.error('Could not fetch configuration')
        return
    
    tmplndconfgen = os.path.join('/tmp', '_'.join(['lndconfgen', 'done.sh']))
    sed_cmd = "sed 's/%%HOST%%/{}/g; s/%%USER%%/{}/g; s/%%PASS%%/{}/g' {}/lndconfgen.sh  > {}".format(host, user, pwd, consts.locations.LIGHTNING, tmplndconfgen)

    sp.check_call(sed_cmd, shell=True)
    
    for node in details:
        if node.name not in targets:
            continue

        scp_cmd = 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r {} {}@{}:{}'.format(
            tmplndconfgen,
            node.username, node.hostname,
            smfiles.target.assets(session)
        )
        logging.info(scp_cmd)

        sp.check_call(scp_cmd, shell=True)


def main():
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()
    parser.add_argument("--manifest", help="manifest for cloudlab")
    parser.add_argument("--pvt-key", help="private key (file)")
    parser.add_argument("--session", help="unique session id")
    
    parser.add_argument("--config", help="X:Y,Z")

    args = parser.parse_args()

    pkey = paramiko.Ed25519Key.from_private_key_file(args.pvt_key)

    details = parse_manifest(args.manifest)

    if args.config:
        frm, to = args.config.split(':')
        copy_btc_node(details, pkey, frm, to)
        update_configurations(details, pkey, args.session, frm, to)

if __name__ == '__main__':
    main()
