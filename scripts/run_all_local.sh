#!/usr/bin/env bash
set -e

echo "[SafeBid] Starting Recommendation Service..."
(
  cd recommendation_service
  python run_server.py
) &
RECOMMENDER_PID=$!

# Give RPyC server time to bind the port
sleep 2

echo "[SafeBid] Starting Django Auction Service..."
(
  cd auction_service
  python manage.py runserver
) &
DJANGO_PID=$!

# Clean shutdown on Ctrl+C
trap "echo '[SafeBid] Shutting down...'; kill $RECOMMENDER_PID $DJANGO_PID" SIGINT SIGTERM

wait
