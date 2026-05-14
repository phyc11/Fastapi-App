#!/bin/bash
set -e

ACTIVE_ENV=$(docker ps -q -f name=fastapi-blue)
if [ -n "$ACTIVE_ENV" ]; then
    CURRENT_COLOR="blue"
    TARGET_COLOR="green"
    TARGET_PORT=8002
else
    CURRENT_COLOR="green"
    TARGET_COLOR="blue"
    TARGET_PORT=8001
fi

echo "Current active environment is $CURRENT_COLOR"
echo "Deploying to target environment: $TARGET_COLOR"

docker-compose pull app-$TARGET_COLOR
docker-compose up -d app-$TARGET_COLOR

echo "Waiting for health check on $TARGET_COLOR..."
sleep 10
HEALTH_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' fastapi-$TARGET_COLOR)

MAX_RETRIES=6
RETRY=0
while [ "$HEALTH_STATUS" != "\"healthy\"" ] && [ $RETRY -lt $MAX_RETRIES ]; do
    echo "Health status is $HEALTH_STATUS. Waiting..."
    sleep 5
    HEALTH_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' fastapi-$TARGET_COLOR)
    RETRY=$((RETRY+1))
done

if [ "$HEALTH_STATUS" == "\"healthy\"" ]; then
    echo "$TARGET_COLOR environment is healthy! Deployment successful."
    echo "Switching traffic to $TARGET_COLOR... (Simulated by stopping $CURRENT_COLOR)"
    
    if [ -n "$CURRENT_COLOR" ]; then
        docker-compose stop app-$CURRENT_COLOR
    fi
else
    echo "ERROR: $TARGET_COLOR environment failed to become healthy."
    echo "Initiating rollback..."
    docker-compose stop app-$TARGET_COLOR
    echo "Rollback complete. $CURRENT_COLOR environment remains active."
    exit 1
fi
