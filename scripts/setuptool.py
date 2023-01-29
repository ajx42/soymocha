import sys
import os
import paramiko
import logging
import time

import subprocess as sp
import xml.etree.ElementTree as ET


from collections import namedtuple
from argparse import ArgumentParser

Node = namedtuple('Node', ['name', 'intf_ip', 'host_ip', 'hostname', 'port', 'username'])
ETHEREUM_STR        = 'ethereum'
DATADIR_STR         = 'datadir'
BUILDDIR_STR        = 'build'
ASSETS_STR          = 'assets'
INSTALL_FILE_STR    = 'install.sh'
ACCOUNT_LOGS_STR    = 'logs.txt'
TMUX_STR            = 'tmux'
BOOTNODE_STR        = 'bootnode'
NODE_STR            = 'node'
BOOTNODE_IDX        = 0

def get_local_assets(app):
    return os.path.join(os.environ['PROJ_HOME'], ASSETS_STR, app)

def get_local_builddir():
    return os.path.join(os.environ['PROJ_HOME'], BUILDDIR_STR)

def get_target_assets(app, session):
    return '_'.join([ASSETS_STR, app, session])

def get_target_datadir(app, session):
    return os.path.join(get_target_assets(app, session), DATADIR_STR)

def get_target_install_script(app, session):
    return os.path.join(get_target_assets(app, session), INSTALL_FILE_STR)

def get_target_account_logs(app, session):
    return os.path.join(get_target_datadir(app, session), ACCOUNT_LOGS_STR)

def get_tmux_script(session):
    return os.path.join(get_local_builddir(), '.'.join([TMUX_STR, session, 'sh']))

def get_ethereum_bootnode_script(session):
    return os.path.join(get_local_builddir(), '.'.join([BOOTNODE_STR, session, 'sh']))

def get_ethereum_node_script(session):
    return os.path.join(get_local_builddir(), '.'.join([NODE_STR, session, 'sh']))

def get_launch_script(app, session):
    pass

# copy over relevant files and install libraries
def install_node(node, pkey, session):
    asset_dir = get_local_assets(ETHEREUM_STR)
    target_assets = get_target_assets(ETHEREUM_STR, session)
    target_filename = get_target_install_script(ETHEREUM_STR, session)

    logging.info('Preparing Node: {}'.format(node.name))

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=node.hostname, username=node.username, port=node.port, pkey=pkey)
    stdin,stdout,stderr = client.exec_command("rm -rf {}".format(target_assets)) 
     
    logging.info('Copying: {}'.format(asset_dir))
    scp_cmd = 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r {} {}@{}:{}'.format(
        asset_dir, node.username, node.hostname, target_assets
    )
    logging.info(scp_cmd)
    sp.check_call(scp_cmd, shell=True)

    stdin,stdout,stderr = client.exec_command("mkdir {}".format(get_target_datadir(ETHEREUM_STR, session))) 
    stdin,stdout,stderr = client.exec_command("chmod +x {}".format(target_filename)) 
    stdin,stdout,stderr = client.exec_command("./{}".format(target_filename))
    for line in stdout.readlines(): print(line.strip())
    for line in stderr.readlines(): print(line.strip())
    client.close()
    # hopefully everything installed! 
    # error checks left as an exercise to the reader

def init_node_tmux(node, session):
    ssh_cmd = 'ssh -oStrictHostKeyChecking=no -p {} {}@{}'.format(
        node.port, node.username, node.hostname
    )
    script = '''\

tmux new-window -d -t {0} -n {1}
tmux select-window -t '={1}'
tmux split-window -h
tmux send-keys -t 0 "{2}" Enter
tmux send-keys -t 1 "{2}" Enter
    '''.format(
        session, node.name, ssh_cmd, 
        get_target_datadir(ETHEREUM_STR, session),
        get_target_account_logs(ETHEREUM_STR, session))
    return script

def init_node_ethereum(node, session):
    script = '''\

tmux select-window -t '={0}'
tmux send-keys -t 1 "sleep 30" Enter
tmux send-keys -t 0 "yes '' | geth account new --datadir {1} |& tee -a {2}" Enter
tmux send-keys -t 0 "sleep 10" Enter
tmux send-keys -t 0 "yes '' | geth init --datadir {1} {3}/genesis.json |& tee -a {2}" Enter
tmux send-keys -t 0 "sleep 5" Enter
tmux send-keys -t 0 "tree -a {3} |& tee -a {2}" Enter
tmux send-keys -t 0 "ifconfig |& tee -a {2}" Enter

    '''.format(
            node.name,
            get_target_datadir(ETHEREUM_STR, session),
            get_target_account_logs(ETHEREUM_STR, session),
            get_target_assets(ETHEREUM_STR, session)
        )
    return script

def generate_tmux_script(details, session):
    filename = get_tmux_script(session)
    if not os.path.exists(get_local_builddir()):
        os.makedirs(get_local_builddir())
    logging.info('Generating TMUX_STR Script: {}'.format(filename))
    with open(filename, 'w') as ff:
        ff.write('''\
#! /bin/bash
echo Session={0}
tmux kill-session -t {0}
tmux new -d -s {0}
tmux new-window -d -t '={0}' -n main
        '''.format(session))

        # create node windows
        for node in details:
            ff.write(init_node_tmux(node, session))
        
        # attach final tmux setup
        ff.write("""\

tmux select-window -t '=main'
        """.format(session))

    sp.check_call('chmod +x {}'.format(filename), shell=True)

def generate_ethereum_bootnode_script(bootnode, session):
    filename = get_ethereum_bootnode_script(session)
    logging.info('Generating ethereum bootnode script: {}'.format(filename))

    with open(filename, 'w') as ff:
        ff.write('''\

#! /bin/bash
echo Session={0}
tmux switch -t {0}
        '''.format(session))

        ff.write(init_node_ethereum(bootnode, session))

        ff.write('''\

tmux send-keys -t 1 "geth --datadir {0} --networkid 16 --nat extip:{1}" Enter
tmux send-keys -t 0 "sleep 30" Enter
tmux send-keys -t 0 "geth attach --exec admin.nodeInfo.enr {0}/geth.ipc" Enter
tmux send-keys -t 0 "geth attach {0}/geth.ipc" Enter
        '''.format(
                get_target_datadir(ETHEREUM_STR, session), bootnode.intf_ip
            )
        )
        
    sp.check_call('chmod +x {}'.format(filename), shell=True)

def generate_ethereum_node_script(details, session, bootnodeenr):
    filename = get_ethereum_node_script(session)
    logging.info('Generating ethereum node script: {}'.format(filename))
    with open(filename, 'w') as ff:
        ff.write('''\

#! /bin/bash
echo Session={0}
tmux switch -t {0}
        '''.format(session))
        for idx, node in enumerate(details):
            if idx == BOOTNODE_IDX:
                continue
            ff.write(init_node_ethereum(node, session))
            ff.write('''\
tmux send-keys -t 0 "sleep 30" Enter
tmux send-keys -t 1 "geth --datadir {0} --networkid 16 --port {1} --bootnodes '{2}'" Enter
tmux send-keys -t 0 "geth attach {0}/geth.ipc" Enter
            '''.format(get_target_datadir(ETHEREUM_STR, session), 30305+idx, bootnodeenr))
    
    sp.check_call('chmod +x {}'.format(filename), shell=True)

def parse_manifest(manifest):
    tree = ET.parse(manifest)
    root = tree.getroot()

    # is this subject to change?
    nsmap = {'ns': 'http://www.geni.net/resources/rspec/3'}

    details = []

    for node in root.findall('ns:node', nsmap):
        name = node.get('client_id')
        intf_ip = node.find('ns:interface', nsmap).find('ns:ip', nsmap).get('address')
        host_ip = node.find('ns:host', nsmap).get('ipv4')
        auth = node.find('ns:services', nsmap).find('ns:login', nsmap)
        hostname = auth.get('hostname')
        port = auth.get('port')
        username = auth.get('username')
        details.append(Node(name=name, intf_ip=intf_ip, host_ip=host_ip, hostname=hostname, port=port, username=username))

    return details

def read_enr(node, pkey, session):
    logging.info('Attempting to read bootnode enr (node record)')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=node.hostname, username=node.username, port=node.port, pkey=pkey)
    stdin,stdout,stderr = client.exec_command(
        "geth attach --exec admin.nodeInfo.enr {0}/geth.ipc".format(get_target_datadir(ETHEREUM_STR, session))) 
    enr = stdout.readlines()[0].strip()
    logging.info('Read record: {}'.format(enr))
    client.close()
    return enr

def handle_ethereum(details, pkey, session):
    logging.info('== Installing Ethereum Tools ==')
    for node in details:
        install_node(node, pkey, session)
    
    logging.info('Initialising tmux session: {}'.format(session))
    sp.check_call('{}'.format(get_tmux_script(session)), shell=True)

    generate_ethereum_bootnode_script(details[BOOTNODE_IDX], session)

    logging.info('Working to setup bootnode at: {}'.format(details[BOOTNODE_IDX].name))
    sp.check_call('{}'.format(get_ethereum_bootnode_script(session)), shell=True)

    logging.info('Sleeping while bootnode setup is in progress')
    time.sleep(45)

    bootnode_enr = read_enr(details[BOOTNODE_IDX], pkey, session)

    generate_ethereum_node_script(details, session, bootnode_enr)

    logging.info('Working to setup other nodes')
    sp.check_call('{}'.format(get_ethereum_node_script(session)), shell=True)

    logging.info('Sleeping while other node setup is in progress')
    time.sleep(45)

    sp.check_call('tmux attach -t {}'.format(session), shell=True)
    
def main():
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()
    
    parser.add_argument("--manifest", help="manifest for cloudlab")
    parser.add_argument("--pvt-key", help="private key (file)")
    parser.add_argument("--session", help="unique session identifier")
    parser.add_argument("--app", help="which app to prepare (currently only ethereum)")
    args = parser.parse_args()

    # !!! this will fail if you use RSA, change the following accordingly
    pkey = paramiko.Ed25519Key.from_private_key_file(args.pvt_key)
    session = args.session

    details = parse_manifest(args.manifest)

    logging.info('Discovered N={} Nodes: {}'.format(len(details), details))
    logging.info('Authentication enabled via ssh keys only')

    # generate tmux setup
    generate_tmux_script(details, session)
    
    if args.app == ETHEREUM_STR:
        # prepare remote hosts: copy over data, install relevant libraries
        handle_ethereum(details, pkey, session)
    else:
        logging.error('Unsupported application. Check back again later!')
        exit(1)


if __name__ == '__main__':
    main()
