export GOPATH=/usr/local/go
export GOROOT=$HOME/go
export PATH=$PATH:$GOPATH/bin:$GOROOT/bin

alias lnd-ws="lnd --lnddir=$HOME/.lnd"
alias lncli-ws="lncli --lnddir=$HOME/.lnd --network=simnet"
