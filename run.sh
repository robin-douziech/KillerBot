#!/bin/bash

if [ -d venv ]
then
        echo "Removing virtual environment"
        rm -r venv
fi

echo "Creating new virtual environment"
python3 -m venv venv

echo "Activating virtual environment"
source venv/bin/activate

echo "Installing dependencies"
pip install -r requirements.txt

echo "Running KillerBot"
nohup python3 src/main.py &
