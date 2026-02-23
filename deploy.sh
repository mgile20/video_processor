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

echo "✅ Done! Image is ready at $IMAGE_NAME:latest"