#!/bin/bash

echo "*Starting Tunneling*"

/home/pi/Desktop/wstunnel -v -L 127.0.0.1:65001:127.0.0.1:65001 wss://<IP_SERVER> &

echo "*Starting TCPClientRSASerialRaspberry*"

nohup python3 /home/pi/Desktop/TCPClientRSASerialRaspberry.py $1 &

echo "*TCPClientRSASerialRaspberry Started*"