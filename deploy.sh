#!/bin/bash

# Determine which backend version is active
ACTIVE_BACKEND=$(docker ps --format "{{.Names}}" | grep fastapi-backend-blue || true)

if [ "$ACTIVE_BACKEND" == "fastapi-backend-blue" ]; then
    echo "Deploying to Green..."
    docker-compose up -d backend-green
    sleep 5  # Allow time for startup

    # Update Nginx to point to the Green backend
    sudo sed -i 's/fastapi-backend-blue/fastapi-backend-green/' /etc/nginx/conf.d/photoguests.conf
    sudo systemctl restart nginx

    # Stop the Blue backend
    docker-compose stop backend-blue
else
    echo "Deploying to Blue..."
    docker-compose up -d backend-blue
    sleep 5

    # Update Nginx to point to the Blue backend
    sudo sed -i 's/fastapi-backend-green/fastapi-backend-blue/' /etc/nginx/conf.d/photoguests.conf
    sudo systemctl restart nginx

    # Stop the Green backend
    docker-compose stop backend-green
fi
