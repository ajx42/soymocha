#! /bin/bash
yes | sudo add-apt-repository -y ppa:ethereum/ethereum || true
yes | sudo apt-get update || true
yes | sudo apt-get install ethereum || true
yes | sudo apt-get install tree || true