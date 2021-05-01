#!/bin/bash
black main.py
export FLASK_APP=main.py
export FLASK_ENV=development
export FLASK_RUN_PORT=8080
flask run --host=0.0.0.0
