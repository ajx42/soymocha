import os
import logging
import sys
import paramiko
import subprocess as sp

from smparser import parse_manifest
from smutils import consts, smfiles, get_connections
from argparse import ArgumentParser

# run setup script on all nodes
# copy over important config files

def copy_location(details, session, location, pkey):
    for node, client in zip(details, get_connections(details, pkey)):
        s_in, s_out, s_err = client.exec_command(
            "mkdir -p {}".format(smfiles.target.assets(session)))

        scp_cmd = 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r {} {}@{}:{}'.format(
            location,
            node.username, node.hostname,
            smfiles.target.assets(session)
        )
        logging.info(scp_cmd)

        sp.check_call(scp_cmd, shell=True)
        for line in out.readlines(): print(line.strip())
        for line in err.readlines(): print(line.strip())


def run_setupnode(details, session, pkey):
    for client in get_connections(details, pkey):
        client.exec_command(
            "chmod +x {}".format(smfiles.target.setupnode(session)))

        _, out, err = client.exec_command(
            "./{}".format(smfiles.target.setupnode(session)))
        
        for line in out.readlines(): print(line.strip())
        for line in err.readlines(): print(line.strip())

        client.exec_command(
            "cp -rT {} .".format(smfiles.target.install(session)))

def run_installall(details, session, pkey):
    for node, client in zip(details, get_connections(details, pkey)):
        logging.info('Installing Lightning Utils on: {}'.format(node.name))
        client.exec_command(
            "chmod +x {}".format(smfiles.target.lightning_installall(session)))

        _, out, err = client.exec_command(
            "./{}".format(smfiles.target.lightning_installall(session)))

        for line in out.readlines(): print(line.strip())
        for line in err.readlines(): print(line.strip())

def clear_location(location, details, pkey):
    for node, client in zip(details, get_connections(details, pkey)):
        logging.info('Clearing at Node={} Location={}'.format(node.name, location))
        
        # let's not remove it, since it is risky
        client.exec_command('mkdir -p /tmp/backup')
        client.exec_command(
            'mv {0} /tmp/backup/{1}'.format( location, os.path.basename(location) ) )


def main():
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()
    parser.add_argument("--manifest", help="manifest for cloudlab")
    parser.add_argument("--pvt-key", help="private key (file)")
    parser.add_argument("--session", help="unique session id")
    
    parser.add_argument("--app", help="copy assets for specific app")
    parser.add_argument("--clear", help="clear app specific config", action='store_true')

    args = parser.parse_args()

    pkey = paramiko.Ed25519Key.from_private_key_file(args.pvt_key)
    
    details = parse_manifest(args.manifest)

    logging.info('Discovered N={} Nodes: {}'.format(len(details), details))
    logging.info('Authentication enabled via ssh keys only')

    if not args.app:
        # this means we are doing a general node setup
        copy_location(details, args.session, consts.locations.INSTALLDIR, pkey)
        run_setupnode(details, args.session, pkey)
    elif args.app == consts.keywords.LIGHTNING:
        if not args.clear:
            copy_location(details, args.session, consts.locations.LIGHTNING, pkey)
            run_installall(details, args.session, pkey)
        else:
            clear_location(".btcd", details, pkey)
            clear_location(".lnd", details, pkey)
            clear_location(".btcctl", details, pkey)

if __name__ == '__main__':
    main()
