#!/bin/bash

# Remove all docker containers

docker rm -f $(docker ps -aq)
