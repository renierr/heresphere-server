#!/bin/bash

# Start the server
source .venv/bin/activate
pip3 install --upgrade -r requirements.txt
python3 main.py
deactivate


