#!/bin/bash

echo $(ps aux | grep '[p]ython3 /home/pi/Desktop/ServerTCP.py' | awk '{print $2}')
