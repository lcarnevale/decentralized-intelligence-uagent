#!/bin/bash

port=$1
src_directory=src

for file in "$src_directory"/*
do
    echo "pushing $file ..."
    ampy --port $port put $file
done