#!/bin/bash

# end script immediately if any commands fail
set -e  

LOG_PATH=/home/ubuntu/logs

echo "Starting RabbitMQ"
mkdir -p "$LOG_PATH/rabbitmq"
rabbitmq-server \
  1> "$LOG_PATH/rabbitmq/stdout.log" \
  2> "$LOG_PATH/rabbitmq/stderr.log" \
  &

echo "Starting Redis"
mkdir -p "$LOG_PATH/redis"
redis-server \
  1> "$LOG_PATH/redis/stdout.log" \
  2> "$LOG_PATH/redis/stderr.log" \
  &

echo "Starting MongoDB"
mkdir -p "$LOG_PATH/mongodb"
mongod --noauth --bind_ip_all --dbpath=/home/ubuntu/mongo/db \
  1> "$LOG_PATH/mongodb/stdout.log" \
  2> "$LOG_PATH/mongodb/stderr.log" \
  &

cd girder/
exec tox "$@"
