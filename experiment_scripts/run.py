import docker
import argparse
import time
from multiprocessing import Pool


def parse_initiator_log(log):
    """Parse the initiator log to get --path and --auth-token values for the responder"""
    path = None
    token = None
    chunks = log.split('\n')
    for chunk in chunks:
        stripped_chunk = chunk.strip()
        if stripped_chunk.startswith("--path"):
            path = stripped_chunk.split(' ')[1].strip()
        elif stripped_chunk.startswith("--auth-token"):
            token = stripped_chunk.split(' ')[1].strip()
    return {'path': path, 'auth-token': token}


def connect(cid, cpus):
    """Connect a pair of clients (initiator and responder)
    cid: unique integer ID which will be used for both clients
    cpus: str of CPUs available for both clients (format is the same as accepted by Docker)"""
    # Set up the volume (volume will be created if not already exist)
    saltyrtc_volume = docker.types.Mount("/saltyrtc-client-rs/logs", 
                                         "saltyrtc-volume",
                                         type="volume")

    # Note: tty must set to be True so that an initiator and a responder can communicate after a connection between them is established
    initiator = daemon.containers.run("saltyrtc-client",
                                      remove=True,
                                      auto_remove=True,
                                      detach=True,
                                      network="saltyrtc",
                                      cpuset_cpus=cpus,
                                      name="initiator-{}".format(cid),
                                      mounts=[saltyrtc_volume],
                                      tty=True)
    conn_info = parse_initiator_log(initiator.logs().decode())
    # responder will be running on the same CPUs as the initiator
    responder = daemon.containers.run("saltyrtc-client",
                                      ["responder", "--path", conn_info['path'], "--auth-token", conn_info['auth-token']],
                                      remove=True,
                                      auto_remove=True,
                                      detach=True,
                                      network="saltyrtc",
                                      cpuset_cpus=cpus,
                                      name="responder-{}".format(cid),
                                      mounts=[saltyrtc_volume],
                                      tty=True)


# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-n', '--connections',
                    help="# of steady state initiator-responder pairs in the server",
                    type=int, default=0)
parser.add_argument('-p', '--cpus', 
                    help="number of available CPUs to run clients (default to 14 assuming a total of 16 CPUs, but one, CPU0, is used to run the server)", default=15)
parser.add_argument('-k', '--kill',
                    help="use this argument to stop all containers",
                    action='store_true')
args = parser.parse_args()

# Connect to a Docker daemon
daemon = docker.from_env()

# If we want to use this script to simply stop all containers
if args.kill:
    containers = daemon.containers.list(all=True)
    for container in containers:
        container.stop()
    exit(0)

# Set up the volume for the server (volume will be created if not already exist)
saltyrtc_volume = docker.types.Mount("/usr/src/saltyrtc-server/saltyrtc/server/logs", 
                                     "saltyrtc-volume",
                                     type="volume")
# Create the SaltyRTC server container
server = daemon.containers.create("saltyrtc-server",
                                  auto_remove=True,
                                  cpuset_cpus="0",
                                  detach=True,
                                  mounts=[saltyrtc_volume],
                                  name="saltyrtc-server")
# Connect the server to a specific IP on a specific network
# Assume we already have the network named "saltyrtc" (172.19.0.0/20) set up
# (directly through the docker network command)
# You can also set it up using the Python code below
# 
# ipam_pool = docker.types.IPAMPool(subnet='172.19.0.0/20')
# ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
# network = daemon.networks.create("saltyrtc", driver="bridge", ipam=ipam_config)
daemon.networks.get("saltyrtc").connect(server, ipv4_address="172.19.0.2")
# Run the server in the background
server.start()

# Create a SaltyRTC client container (initiator)
# Assume we already have a volume called "saltyrtc-volume" set up
# (directly through the docker volume command, see client.sh)
# You can also set it up using Docker SDK for Python, check docs
#
# Set up the volume
saltyrtc_volume = docker.types.Mount("/saltyrtc-client-rs", 
                                     "saltyrtc-volume",
                                     type="volume")
# Set up N initiators (for steady state)
for i in range(args.connections):
    cpu = i % args.cpus + 1   # Each initiator uses a destinated CPU (except CPU0)
    connect(i, str(cpu))

time.sleep(2)

with Pool(processes=4) as pool:
    pool.starmap(connect, [(1, '5'), (2, '6')])

