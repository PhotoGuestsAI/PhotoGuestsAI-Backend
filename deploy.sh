#!/bin/bash

# Ensure script runs from the correct directory
cd ~/PhotoGuestsAI-Backend

# Function to determine the active backend
get_active_backend() {
    if docker ps --format "{{.Names}}" | grep -q "fastapi-backend-blue"; then
        echo "blue"
    else
        echo "green"
    fi
}

ACTIVE_BACKEND=$(get_active_backend)

if [ "$ACTIVE_BACKEND" == "blue" ]; then
    echo "Deploying to Green..."
    docker-compose up -d backend-green
    sleep 5  # Allow time for startup

    # Stop Blue backend
    docker-compose stop backend-blue
else
    echo "Deploying to Blue..."
    docker-compose up -d backend-blue
    sleep 5  # Allow time for startup

    # Stop Green backend
    docker-compose stop backend-green
fi
