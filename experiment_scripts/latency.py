import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import csv
from datetime import datetime


# def get_time_from_log(log_path):
#     """Extract time information from the log file"""
#     server_handshake_start_time = None     # time to start the handshake with the server
#     server_handshake_end_time = None       # time when server handshake is done
#     peer_handshake_start_time = None       # time to start the handshake with the peer
#                                            # If responder, this value will remain None
#     peer_handshake_end_time = None         # time when peer handshake is done
#     with open(log_path, 'r') as log:
#         for line in log:
#             # A line will look like this:
#             # 2022-01-20T00:51:45.283 [WARN ] Connected to server as Initiator (src/lib.rs:474)
#             # We split it into 4 parts:
#             # 1. datetime: 2022-01-20T00:51:45.283
#             # 2. [WARN
#             # 3. ]
#             # 4. Connected to server as Initiator (src/lib.rs:474)
#             data = line.split(" ", 3)
#             time = data[0]
#             content = data[3].strip()
#             if content.startswith("Connected to server as Initiator"):
#                 server_handshake_start_time = datetime.fromisoformat(time)
#             elif content.startswith("Connected to server as Responder"):
#                 server_handshake_start_time = datetime.fromisoformat(time)
#             elif content.startswith("Server handshake completed"):
#                 server_handshake_end_time = datetime.fromisoformat(time)
#             elif content.startswith("Registering new responder"):
#                 peer_handshake_start_time = datetime.fromisoformat(time)
#             elif content.startswith("Peer handshake done"):
#                 peer_handshake_end_time = datetime.fromisoformat(time)
#     return {'server_start': server_handshake_start_time,
#             'server_end': server_handshake_end_time,
#             'peer_start': peer_handshake_start_time,
#             'peer_end': peer_handshake_end_time}

def parse_latency_stats(fp):
    """
    Parse latency statistics.
    :param fp: the file path that stores the statistics
    :returns an average latency in milliseconds to connect a pair of initiator and responder clients
    """
    latency = []
    with open(fp) as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=' ', fieldnames=['title', 'time'])
        for row in csvreader:
            latency.append(float(row['time']) * 1000)
    return sum(latency) / len(latency)


def workload_latency_chart(labels, latency, latency_splice, emulated, outfile):
    """
    Plot client (initiator and responder peers) perceived latency.
    :param labels: a list of numbers of clients in the experiment, e.g., [1, 2, 4, 8, 16, 32]
    :param latency: latency (in milliseconds) corresponds to labels
    :param latency_splice: same as latency, but the splice results
    :param emulated: whether network emulation is on
    :param outfile: output file path
    """
    x = labels
    fig, ax = plt.subplots()

    latency = np.array(latency)
    latency_splice = np.array(latency_splice)

    ax.plot(x, latency, color=mcolors.CSS4_COLORS['darkblue'], marker='o',
            label='Baseline (100 RTT)' if emulated else 'Baseline (0 RTT)')
    ax.plot(x, latency_splice, color=mcolors.CSS4_COLORS['darkgreen'], marker='^',
            label='Splice (100 RTT)' if emulated else 'Splice (0 RTT)')

    # ax.set_ylim(0, 100)
    ax.set_xlabel('# of Concurrent Initiator/Responder Client Peers')
    ax.set_ylabel('Latency (milliseconds)')
    ax.set_title('SaltyRTC Client-perceived Latency')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(loc='lower right')

    fig.tight_layout()
    # plt.show()
    plt.savefig(outfile)


def parse_all_workload_data(clients):
    """
    Parses all data from running the workload.
    :param clients: a list of numbers of clients from small to large, e.g., [1,2,4,8]
    """
    latency = []
    latency_splice = []
    latency_emulated = []
    latency_splice_emulated = []

    for client in clients:
        fp = "./latency_data/clients_0_{}.log".format(client)
        fp_splice = "./latency_data/clients_0_{}_splice.log".format(client)
        fp_emulated = "./latency_data/clients_0_{}_latency.log".format(client)
        fp_emulated_splice = "./latency_data/clients_0_{}_splice_latency.log".format(client)

        r = parse_latency_stats(fp)
        r_s = parse_latency_stats(fp_splice)
        r_e = parse_latency_stats(fp_emulated)
        r_s_e = parse_latency_stats(fp_emulated_splice)

        latency.append(r)
        latency_splice.append(r_s)
        latency_emulated.append(r_e)
        latency_splice_emulated.append(r_s_e)

    workload_latency_chart(clients, latency, latency_splice, False, 'latency')
    workload_latency_chart(clients, latency_emulated, latency_splice_emulated, True, 'latency_emulated')


if __name__ == '__main__':
    parse_all_workload_data([1, 2, 4, 8, 16, 32, 64, 128, 256, 512])
