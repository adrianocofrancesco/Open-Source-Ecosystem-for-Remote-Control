#!/bin/bash

echo "*Starting ClientTCP...*"

HOST_IP=$(route -n | grep 'UG[ \t]' | awk '{print $2}')
echo $HOST_IP

# Uncomment for Tunneling http
nohup python3 /home/pi/Desktop/ClientTCP.py $HOST_IP &

# Uncomment for WIREGUARD
#nohup python3 /home/pi/Desktop/ClientTCPWireguard.py $HOST_IP &

echo "*ClientTCP Started!*"
