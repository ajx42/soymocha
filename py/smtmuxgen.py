import os
import sys
import logging
import paramiko
import subprocess as sp

import smparser

from smutils import smfiles, consts
from argparse import ArgumentParser

def __init_node_tmux(node, session):
    ssh_cmd = 'ssh -oStrictHostKeyChecking=no -p {} {}@{}'.format(
        node.port, node.username, node.hostname
    )
    script = '''\

tmux new-window -d -t {0} -n {1}
tmux select-window -t '={1}'
tmux split-window -h
tmux send-keys -t 0 "{2}" Enter
tmux send-keys -t 1 "{2}" Enter
    '''.format(session, node.name, ssh_cmd)
    
    return script

def generate_tmux_script(details, session):
    filename = smfiles.generated.tmux_script(session)
    builddir = consts.locations.BUILDDIR

    if not os.path.exists(builddir):
        os.makedirs(builddir)
    
    logging.info('Generating TMUX Script: {}'.format(filename))
    
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
            ff.write(__init_node_tmux(node, session))
        
        # attach final tmux setup
        ff.write("""\

tmux select-window -t '=main'
        """.format(session))

    sp.check_call('chmod +x {}'.format(filename), shell=True)

def main():
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()

    parser.add_argument("--manifest", help="manifest for cloudlab")
    parser.add_argument("--session", help="(hopefully) unique session identifier")

    parser.add_argument("--launch", action='store_true', help="launch tmux")

    args = parser.parse_args()

    details = smparser.parse_manifest(args.manifest)
    logging.info('Discovered N={} Nodes: {}'.format(len(details), details))

    generate_tmux_script(details, args.session)

    if args.launch:
        pass

if __name__ == '__main__':
    main()
