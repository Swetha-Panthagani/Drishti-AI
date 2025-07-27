#!/bin/sh
source .venv/bin/activate
python -u -m flask --app main run --port=$PORT --debug