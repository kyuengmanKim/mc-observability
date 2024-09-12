#!/bin/sh

cd $HOME

docker -v
if [ $? -ne 0 ]; then
  # Install Docker CE
  sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli docker-compose-plugin
fi

wget --version
if [ $? -ne 0 ]; then
  sudo apt-get install -y wget
fi
mkdir -p mc-observability/
wget https://raw.githubusercontent.com/m-cmp/mc-observability/main/java-module/docker-compose.yaml -O mc-observability/docker-compose.yaml

cd mc-observability/

cat <<EOF > .env
NS_ID=$2
MCI_ID=$3
TARGET_ID=$4
DATABASE_HOST=$1
DATABASE_NAME=mc-observability
DATABASE_ID=mc-agent
DATABASE_PW=mc-agent
EOF

sudo docker compose up -d