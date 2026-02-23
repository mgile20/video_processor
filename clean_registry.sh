#!/bin/bash

# Configuration
REGISTRY_URL="localhost:5000"
REPO_NAME=$1

if [ -z "$REPO_NAME" ]; then
    echo "Usage: ./clean_registry.sh [repository_name]"
    exit 1
fi

echo "--- Fetching all tags for $REPO_NAME ---"

# 1. Get the list of all tags
TAGS=$(curl -s "http://$REGISTRY_URL/v2/$REPO_NAME/tags/list" | jq -r '.tags[]')

if [ -z "$TAGS" ] || [ "$TAGS" == "null" ]; then
    echo "No tags found for $REPO_NAME."
    exit 1
fi

for TAG in $TAGS; do
    if [ "$TAG" == "latest" ]; then
        echo "Skipping: $TAG (Keeping this version)"
        continue
    fi

    echo "Processing deletion for: $TAG"

    # 2. Get the Digest for the specific tag
    # We must include the specific Accept header to get the correct V2 digest
    DIGEST=$(curl -I -s -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
        "http://$REGISTRY_URL/v2/$REPO_NAME/manifests/$TAG" \
        | grep -i Docker-Content-Digest \
        | awk '{print $2}' \
        | tr -d $'\r')

    if [ -n "$DIGEST" ]; then
        # 3. Delete the manifest
        echo "  Deleting manifest $DIGEST..."
        curl -X DELETE -s "http://$REGISTRY_URL/v2/$REPO_NAME/manifests/$DIGEST"
    else
        echo "  Failed to find digest for $TAG"
    fi
done

# 4. Final Garbage Collection
echo "--- Triggering Registry Garbage Collection ---"
docker exec local-registry bin/registry garbage-collect /etc/docker/registry/config.yml

echo "--- Cleanup Complete ---"