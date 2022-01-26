import glob
import docker
import argparse
import time
import logging
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
    """
    Connect a pair of clients (initiator and responder) through the server.
    daemon is the docker Python client.
    cid: unique integer ID which will be used for both clients
    cpus: str of CPUs available for both clients (format is the same as accepted by Docker)
    """
    # Set up the volume for clients (volume will be created if not already exist)
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
                                      tty=True,
                                      stderr=True)
    # We need to give the client (initiator) a bit of time to setup
    time.sleep(0.5)
    # print("initiator-{}: {}".format(cid, initiator.logs(stdout=True, stderr=True)))
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
                                      tty=True,
                                      stderr=True)
    # logging.error("responder-{}: {}".format(cid, responder.logs(stdout=True, stderr=True)))


def serve():
    """Set up and run the server"""
    # Set up the volume for the server (volume will be created if not already exist)
    saltyrtc_volume = docker.types.Mount("/usr/src/saltyrtc-server/saltyrtc/server/logs", 
                                         "saltyrtc-volume",
                                         type="volume")
    # Create the SaltyRTC server container. The server container always runs on CPU 0.
    server = daemon.containers.create("saltyrtc-server",
                                      auto_remove=True,
                                      cpuset_cpus="0",
                                      detach=True,
                                      mounts=[saltyrtc_volume],
                                      cap_add=["NET_ADMIN"],
                                      name="saltyrtc-server")
    # Connect the server to a specific IP on a specific network
    # Assume we already have the network named "saltyrtc" (172.19.0.0/20) set up
    # (directly through the docker network command)
    # You can also set it up using the Python code below
    # 
    # ipam_pool = docker.types.IPAMPool(subnet='172.19.0.0/20')
    # ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
    # network = daemon.networks.create("saltyrtc", driver="bridge", ipam=ipam_config)
    #
    daemon.networks.get("saltyrtc").connect(server, ipv4_address="172.19.0.2")
    # Run the server in the background
    server.start()
    # Add latency to the outbound traffic from the server
    server.exec_run(["tc", "qdisc", "add", "dev", "eth1", "root", "netem", "delay", "100ms", "5ms"])


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--serve', help="start the server", action='store_true')
    parser.add_argument('-n', '--connections',
                        help="# of steady state initiator-responder pairs in the server",
                        type=int, default=0)
    parser.add_argument('-p', '--cpus', 
                        help="number of available CPUs to run clients (default to 15 assuming a total of 16 CPUs, but one, CPU0, is always used to run the server)", default=15)
    parser.add_argument('-m', '--multiple',
                        help="# of new initiator-responder pairs connecting to the server at a time", type=int, default=0)
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

    # Set up logging
    logging.basicConfig(filename="run.log", level=logging.INFO)

    # Either set up the server of set up the clients
    if args.serve:
        serve()
        print("[SUCCESS] server is running.")
    else:
        # Set up N initiators (for steady state)
        for i in range(args.connections):
            # cpu = i % args.cpus + 1       # Each initiator/responder uses a destinated CPU (except CPU0)
            # cpu = "1-{}".format(args.cpus)  # Clients share all CPU resources except the one for the server
            cpu = "1"
            connect(i, str(cpu))
        # Give it a bit more time to reach the steady state
        time.sleep(2)
        # We will log the name of the log files of the clients in the steady state
        files = glob.glob("/var/lib/docker/volumes/saltyrtc-volume/_data/chat.*.log")
        for f in files:
            logging.info("{}".format(f))

        # New clients join after steady state
        # Set up for the clients
        new_clients = []
        cpus = "1".format(args.cpus)  # Clients share all CPU resources except the one for the server
        for i in range(args.multiple):
            new_clients.append((args.connections + i, cpus))
        # Run new clients
        with Pool(processes=16) as pool:
            pool.starmap(connect, new_clients)
        print("[SUCCESS] {} clients are running.".format(len(daemon.containers.list(all=True)) - 1))

