#!/bin/bash

echo "*Starting ServerTCP*"

nohup python3 /home/pi/Desktop/ServerTCP.py $1 $2 &

echo "*ServerTCP Started*"
