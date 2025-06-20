#!/bin/bash

sudo systemctl restart nginx.service
sudo systemctl restart gunicorn_django5.service
sudo supervisorctl restart all
sudo systemctl restart mosquitto
sudo systemctl restart pgbouncer

