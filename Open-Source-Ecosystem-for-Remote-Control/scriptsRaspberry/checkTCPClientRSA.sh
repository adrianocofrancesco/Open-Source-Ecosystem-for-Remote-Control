#!/bin/bash

echo $(ps aux | grep '[p]ython3 /home/pi/Desktop/TCPClientRSASerialRaspberry.py' | awk '{print $2}')
