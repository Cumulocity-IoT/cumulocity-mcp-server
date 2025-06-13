#!/bin/bash

docker build -t mcp-c8y -f docker/Dockerfile --platform linux/amd64 .

cd docker

docker save mcp-c8y > "image.tar"

zip mcp-server-c8y cumulocity.json image.tar