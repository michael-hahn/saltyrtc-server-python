#!/bin/sh
# DO NOT RUN THIS SCRIPT!
# This is mostly for note-taking and future reference.

# The SaltyRTC server can easily be run on a Docker container using the Dockerfile provided in this folder.
# The Dockerfile has been modified for Splice. On the Ubuntu 18 test machine, it builds and runs smoothly.
# Read the Dockerfile to see the environmental setup.

# Some references here for Docker (You don't need to run them if you already have Docker installer and running on Linux)
# Install Docker from the official Docker repository to get the latest version.
# Ref: https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04
sudo apt-get install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
sudo apt-get update
sudo apt-get install docker-ce -y
# Check to make sure Docker is in fact running now.
sudo systemctl status docker
# Avoid typing sudo whenever you run the docker command.
sudo usermod -aG docker ${USER}
# To apply the new group membership, log out of the server and back in.
# You will be prompted to enter your user’s password to continue.
su - ${USER}
# Check to confirm that user is now added to the docker group.
id -nG

# Clone this repository to run the server
git clone https://github.com/michael-hahn/saltyrtc-server-python.git
cd ./saltyrtc-server-python

# Create a Docker network called 'saltyrtc'
# You do not need the --driver bridge flag since it’s the default, but this example shows how to specify it.
# Ref: https://docs.docker.com/network/network-tutorial-standalone/#use-user-defined-bridge-networks
docker network create --driver bridge saltyrtc --subnet 172.18.0.0/20
# List Docker’s networks
docker network ls
# Inspect the 'saltyrtc' network. This shows you its IP address and the fact that no containers are connected to it
docker network inspect saltyrtc

# Make sure you have generated correct SSL key and certificate!
# THE SSL CERTIFICATE SHOULD BE ASSOCIATED WITH THE IP OF THE SERVER (SEE BELOW --ip option)!
# THE 'saltyrtc.crt' and 'saltyrtc.key' FILES INCLUDED IN THIS FOLDER WILL NOT WORK ON DOCKER!
# GENERATE NEW ONE USING THIS COMMAND:
openssl req -newkey rsa:1024 \
   -x509 \
   -nodes \
   -keyout saltyrtc.key \
   -new \
   -out saltyrtc.crt \
   -subj /CN=172.19.0.2 \
   -reqexts SAN \
   -extensions SAN \
   -config <(cat /etc/ssl/openssl.cnf \
     <(printf '[SAN]\nsubjectAltName=IP.1:172.19.0.2')) \
   -sha256 \
   -days 1825
# REPLACE THE IP ADDRESS IF NECESSARY!
# You can take a look at the certificate by:
openssl x509 -in saltyrtc.crt -noout -text
# References:
# https://medium.com/@antelle/how-to-generate-a-self-signed-ssl-certificate-for-an-ip-address-f0dd8dddf754
# https://github.com/saltyrtc/saltyrtc-client-rs#setup

# Build the docker image for SaltyRTC
docker build --tag saltyrtc .

# Now you can run the SaltyRTC container
# Use CPU affinity to bind the docker container to a given CPU or CPUs
# Ref: https://docs.docker.com/engine/reference/run/#runtime-constraints-on-resources
# We use our user-defined bridged network 'saltyrtc' to place SaltyRTC on a fixed IP
docker run --rm --cpuset-cpus="0" --network saltyrtc --ip="172.19.0.2" --name=saltyrtc saltyrtc

# To run the experiment using Docker SDK for Python
cd experiment_scripts
# Set up a virtual environment
python3.8 -m venv docker
source docker/bin/activate
# Install Docker SDK for Python
pip install docker


# MORE USEFUL LINKS ====================================================================================================
# SaltyRTC:
## https://saltyrtc.org
## https://lgrahl.de/pub/ba-thesis-saltyrtc-by-lennart-grahl-revised-v1.pdf
# For certificate problem:
# https://letsencrypt.org/docs/certificates-for-localhost/
# https://stackoverflow.com/questions/8169999/how-can-i-create-a-self-signed-cert-for-localhost
# Docker general tutorial
# https://docker-curriculum.com
# For example, common Docker commands:
docker images             # check all existing built images
docker ps -a              # check all existing containers
docker rm [CONTAINER ID]  # remove a container
docker rmi [IMAGE ID]     # remove an image
# Docker networking tutorial
# https://docs.docker.com/network/network-tutorial-standalone/#use-user-defined-bridge-networks
