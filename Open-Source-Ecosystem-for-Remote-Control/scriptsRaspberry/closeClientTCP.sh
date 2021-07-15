#!/bin/bash

echo "*Closing ClientTCP*"

# Uncomment for Tunneling http
kill $(ps aux | grep '[p]ython3 /home/pi/Desktop/ClientTCP.py' | awk '{print $2}')

# Uncomment for WIREGUARD
#kill $(ps aux | grep '[p]ython3 /home/pi/Desktop/ServerTCP.py' | awk '{print $2}')
#sudo wg-quick down BrightService

echo "*ClientTCP Closed*"
