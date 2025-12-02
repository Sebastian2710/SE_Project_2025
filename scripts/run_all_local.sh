#!/usr/bin/env bash

# Run recommender RPyC server
(cd recommendation_service && python run_server.py) &

# Run Django auction service
(cd auction_service && python manage.py runserver) &
