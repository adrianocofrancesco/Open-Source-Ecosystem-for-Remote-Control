#!/bin/bash

echo "*Closing Services*"
kill $(ps aux | grep '[p]ython3 /home/pi/Desktop/TCPClientRSASerialRaspberry.py' | awk '{print $2}')
echo "*TCPClientRSASerialRaspberry Closed*"
kill $(ps aux | grep '[w]stunnel' | awk '{print $2}')
echo "*Wstunnel Closed *"
echo "*Services Closed*"
