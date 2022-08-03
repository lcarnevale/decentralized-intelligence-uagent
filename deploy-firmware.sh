#!/bin/bash

port=$1
firmware=$2

esptool.py --chip esp32 --port $port erase_flash
esptool.py --chip esp32 --port $port --baud 460800 write_flash -z 0x1000 $firmware