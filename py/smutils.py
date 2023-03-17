import os
import paramiko
from types import SimpleNamespace

PROJ_HOME = os.environ['PROJ_HOME']

consts = SimpleNamespace()
consts.locations = SimpleNamespace()
consts.values = SimpleNamespace()
consts.keywords = SimpleNamespace()

consts.locations.BUILDDIR   = os.path.join(PROJ_HOME, 'build')
consts.locations.ASSETSDIR  = os.path.join(PROJ_HOME, 'assets')
consts.locations.INSTALLDIR = os.path.join(consts.locations.ASSETSDIR, 'install')
consts.locations.SETUPNODE  = os.path.join(consts.locations.INSTALLDIR, 'setupnode.sh')
consts.locations.VIMRC      = os.path.join(consts.locations.INSTALLDIR, '.vimrc')
consts.locations.TMUXCONF   = os.path.join(consts.locations.INSTALLDIR, '.tmux.conf')
consts.locations.ZSHRC      = os.path.join(consts.locations.INSTALLDIR, '.zshrc')
consts.locations.LIGHTNING  = os.path.join(consts.locations.ASSETSDIR, 'lightning')

consts.keywords.TMUX = 'tmux'
consts.keywords.ASSETS = 'assets'
consts.keywords.INSTALL = 'install'
consts.keywords.LIGHTNING = 'lightning'

def __get_script(script, session):
    return '.'.join([script, session, 'sh'])

def __get_generated_tmux_script(session):
    return os.path.join(consts.locations.BUILDDIR, __get_script(consts.keywords.TMUX, session))

def __get_target_assets(session):
    return os.path.join(session, consts.keywords.ASSETS)

def __get_target_install(session):
    return os.path.join(__get_target_assets(session), consts.keywords.INSTALL)

def __get_target_setupnode(session):
    return os.path.join(__get_target_install(session), 'setupnode.sh')

def __get_target_lightning_installall(session):
    return os.path.join(__get_target_assets(session), consts.keywords.LIGHTNING, 'installall.sh')

smfiles = SimpleNamespace()
smfiles.generated = SimpleNamespace()
smfiles.target = SimpleNamespace()

smfiles.generated.tmux_script = __get_generated_tmux_script
smfiles.target.assets = __get_target_assets
smfiles.target.setupnode = __get_target_setupnode
smfiles.target.install = __get_target_install
smfiles.target.lightning_installall = __get_target_lightning_installall

def get_connections(details, pkey):
    cons = []
    for node in details:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=node.hostname,
            username=node.username,
            port=node.port,
            pkey=pkey
        )
        cons.append(client)
    return cons

