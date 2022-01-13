# This python script simulates a client sends a Splice deletion request to the SaltyRTC server,
# so that we do not need to modify the RTC client application. To delete a specific client,
# we need to know its unique taint value (this will be printed out in the server console
# when a client is connected to the server). Use this taint value (which should be an int) as
# the argument to run this script for Splice deletion.

# We assume in this script that the SaltyRTC server is at 127.0.0.1. We also assume the existence
# of SSL certificate (saltyrtc.crt) in the parent directory (note that SSL is a must to run this
# client properly). However, these are arguments to this script that should be changed as needed.

import socket
import ssl
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-H', '--host', help='SaltyRTC server IP', default='127.0.0.1')
parser.add_argument('-p', '--port', help='SaltyRTC server port', type=int, default=8765)
parser.add_argument('-c', '--certs', help='path to certificate', default='../saltyrtc.crt')
parser.add_argument('-t', '--taint', help='taint ID of the user to be deleted', type=int, default=549755813888)  # required=True)
args = parser.parse_args()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    with ssl.wrap_socket(s, cert_reqs=ssl.CERT_REQUIRED, ca_certs=args.certs) as ssock:
        ssock.connect((args.host, args.port))
        print("Connected to {}:{}".format(args.host, args.port))
        # Send a simple SPLICE deletion request with taint
        ssock.sendall(bytes('GET {path} HTTP/1.1\r\nTaints: {taints}\r\n\r\n'.
                            format(path='SPLICE', taints=args.taint), 'utf8'))
        data = ssock.recv(1024)
