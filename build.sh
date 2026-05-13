#!/bin/bash
echo "Building the project..."
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
