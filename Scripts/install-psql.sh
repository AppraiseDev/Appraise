#!/bin/bash
which psql
if [ "$?" -gt "0" ]; then
  echo "Not installed"
  apt-get install -y curl ca-certificates gnupg lsb-core
  curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
  sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
  apt-get update
  apt-get install -y postgresql-client-11
fi
