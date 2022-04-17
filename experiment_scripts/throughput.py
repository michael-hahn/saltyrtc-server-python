import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import csv


def parse_throughput_stats(fp):
    """
    Parse throughput statistics.
    :param fp: the file path that stores the statistics
    :returns the number of pairs of initiator and responder clients a server can handle per second
    """
    counter = 0
    with open(fp) as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=' ', fieldnames=['title', 'time'])
        for _ in csvreader:
            counter += 1
    return counter/float(10)    # The experiment lasted for 20 seconds


def workload_latency_chart(labels, throughput, throughput_splice, emulated, outfile):
    """
    Plot number of client-pair (initiator and responder peers) handled by the server per second
    :param labels: a list of numbers of clients in the experiment, e.g., [1, 2, 4, 8, 16, 32]
    :param throughput: throughput (in number of client pairs) corresponds to labels
    :param throughput_splice: same as throughput, but the splice results
    :param emulated: whether network emulation is on
    :param outfile: output file path
    """
    x = labels
    fig, ax = plt.subplots()

    throughput = np.array(throughput)
    throughput_splice = np.array(throughput_splice)

    ax.plot(x, throughput, color=mcolors.CSS4_COLORS['darkblue'], marker='o',
            label='Baseline (100 RTT)' if emulated else 'Baseline (0 RTT)')
    ax.plot(x, throughput_splice, color=mcolors.CSS4_COLORS['darkgreen'], marker='^',
            label='Splice (100 RTT)' if emulated else 'Splice (0 RTT)')

    # ax.set_ylim(0, 100)
    ax.set_xlabel('# of Concurrent Initiator/Responder Client Peers')
    ax.set_ylabel('# of Connected Peers Per Second')
    ax.set_title('SaltyRTC Server Throughput')
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
    throughput = []
    throughput_splice = []
    throughput_emulated = []
    throughput_splice_emulated = []

    for client in clients:
        fp = "./data/clients_{}.log".format(client)
        fp_splice = "./data/clients_{}_splice.log".format(client)
        fp_emulated = "./data/clients_{}_latency.log".format(client)
        fp_emulated_splice = "./data/clients_{}_splice_latency.log".format(client)

        r = parse_throughput_stats(fp)
        r_s = parse_throughput_stats(fp_splice)
        r_e = parse_throughput_stats(fp_emulated)
        r_s_e = parse_throughput_stats(fp_emulated_splice)

        throughput.append(r)
        throughput_splice.append(r_s)
        throughput_emulated.append(r_e)
        throughput_splice_emulated.append(r_s_e)

    workload_latency_chart(clients, throughput, throughput_splice, False, 'throughput')
    workload_latency_chart(clients, throughput_emulated, throughput_splice_emulated, True, 'throughput_emulated')


if __name__ == '__main__':
    parse_all_workload_data([1, 2, 4, 8, 16, 32, 64, 128, 256, 512])
