#!/bin/bash

# --- Configuration ---
REGISTRY="localhost:5000"       # e.g., index.docker.io/username
APP_NAME="video_processor"
VERSION=$(date +%Y%m%d%H%M%S)      # Timestamp for unique versioning
IMAGE_NAME="$REGISTRY/$APP_NAME"

echo "🛠️  Building image..."
docker build -t "$IMAGE_NAME:latest" -t "$IMAGE_NAME:$VERSION" .

# Optional: Log in if not already authenticated
# echo "🔐 Logging into registry..."
# docker login "$REGISTRY"

echo "📤 Pushing version: $VERSION..."
docker push "$IMAGE_NAME:$VERSION"

echo "🔝 Pushing 'latest' tag..."
docker push "$IMAGE_NAME:latest"

echo "🧹 Cleaning up old versions in local registry..."

# 1. Get all tags from the registry API
# We use the API to find the names of the old tags
OLD_TAGS=$(curl -s "http://$REGISTRY/v2/$APP_NAME/tags/list" | jq -r '.tags[]' | grep -v "latest" | grep -v "$VERSION")

if [ -n "$OLD_TAGS" ]; then
    for TAG in $OLD_TAGS; do
        echo "   Removing index for old tag: $TAG"
        # We delete the folder directly to avoid API Header/Digest issues
        docker exec "$REGISTRY_CONTAINER" rm -rf "/var/lib/registry/docker/registry/v2/repositories/$APP_NAME/_manifests/tags/$TAG"
    done

    echo "♻️  Running Garbage Collection to reclaim space..."
    docker exec "$REGISTRY_CONTAINER" bin/registry garbage-collect /etc/docker/registry/config.yml > /dev/null
else
    echo "✨ No old versions to clean."
fi

echo "✅ Done! Image is ready at $IMAGE_NAME:latest"

docker system prune -f