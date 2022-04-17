import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import csv


def parse_cpumem_stats(fp, skip_first, skip_last):
    """
    Parse CPU and memory statistics.
    :param fp: the file path that stores the statistics
    :param skip_first: the number of first several lines to skip (system is not yet steady)
    :param skip_last: the line number (start from 1) of the first line to skip
                      (all lines after that line should be skipped)
    :returns a dictionary containing results for each type of request
    """
    cpu = []
    mem = []
    counter = 0
    with open(fp) as csvfile:
        csvreader = csv.DictReader(csvfile, fieldnames=['time', 'pid', 'virt', 'res', '%cpu', '%mem'])
        for row in csvreader:
            if counter < skip_first or counter >= skip_last:
                counter += 1
            else:
                cpu.append(float(row['%cpu'])/100)
                mem.append(float(row['res'])/1000)
    return {'%cpu': sum(cpu) / len(cpu),
            'mem': sum(mem) / len(mem)}


def workload_cpu_chart(labels, cpu, cpu_splice, cpu_emulated, cpu_emulated_splice, outfile):
    """
    Plot server CPU utilization only.
    :param labels: a list of numbers of clients in the experiment, e.g., [1, 2, 4, 8, 16, 32]
    :param cpu: CPU utilization corresponds to labels
    :param cpu_splice: same as CPU, but the splice results
    :param cpu_emulated: CPU utilization but with network emulation
    :param cpu_emulated_splice: CPU utilization but with network emulation and Splice
    :param outfile: output file path
    """
    x = labels
    fig, ax = plt.subplots()

    cpu = np.array(cpu)
    cpu_splice = np.array(cpu_splice)
    cpu_emulated = np.array(cpu_emulated)
    cpu_emulated_splice = np.array(cpu_emulated_splice)
    ax.plot(x, cpu_emulated, color=mcolors.CSS4_COLORS['darkred'], marker='*', label='Baseline (100 RTT)')
    ax.plot(x, cpu_emulated_splice, color=mcolors.CSS4_COLORS['darkorange'], marker='x', label='Splice (100 RTT)')
    ax.plot(x, cpu, color=mcolors.CSS4_COLORS['darkblue'], marker='o', label='Baseline (0 RTT)')
    ax.plot(x, cpu_splice, color=mcolors.CSS4_COLORS['darkgreen'], marker='^', label='Splice (0 RTT)')

    ax.set_ylim(0, 100)
    ax.set_xlabel('# of Concurrent Initiator/Responder Client Peers')
    ax.set_ylabel('CPU Utilization (%)')
    ax.set_title('SaltyRTC Server CPU Utilization')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(loc='lower right')

    fig.tight_layout()
    # plt.show()
    plt.savefig(outfile)


def workload_mem_chart(labels, mem, mem_splice, emulated, outfile):
    """
    Plot server memory usage only.
    :param labels: a list of numbers of clients in the experiment, e.g., [1, 2, 4, 8, 16, 32]
    :param mem: memory usage corresponds to labels
    :param mem_splice: same as mem, but the splice results
    :param emulated: whether there is network emulation of 100 RTT
    :param outfile: output file path
    """
    x = np.arange(len(labels))  # the label locations
    width = 0.20  # the width of the bars

    fig, ax = plt.subplots()

    # Plot memory data
    mem = np.array(mem)
    mem_s = np.array(mem_splice)

    ax.bar(x - width / 2, mem, width, color=mcolors.CSS4_COLORS['white'],
           edgecolor=mcolors.CSS4_COLORS['black'], label='Baseline (100 RTT)' if emulated else 'Baseline (0 RTT)')
    ax.bar(x + width / 2, mem_s, width, color=mcolors.CSS4_COLORS['black'],
           label='Splice (100 RTT)' if emulated else 'Splice (0 RTT)')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_xlabel('# of Concurrent Initiator/Responder Client Peers')
    ax.set_ylabel('Memory Usage (MB)')
    ax.set_title('SaltyRTC Server Memory Usage')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), fancybox=True, ncol=3)

    fig.tight_layout()
    # plt.show()
    plt.savefig(outfile)


def parse_all_workload_data(clients):
    """
    Parses all data from running the workload.
    :param clients: a list of numbers of clients from small to large, e.g., [1,2,4,8]
    """
    mem = []
    mem_splice = []
    mem_emulated = []
    mem_splice_emulated = []
    cpu = []
    cpu_splice = []
    cpu_emulated = []
    cpu_splice_emulated = []

    for client in clients:
        fp = "./data/cpumem_{}.log".format(client)
        fp_splice = "./data/cpumem_{}_splice.log".format(client)
        fp_emulated = "./data/cpumem_{}_latency.log".format(client)
        fp_emulated_splice = "./data/cpumem_{}_splice_latency.log".format(client)

        r = parse_cpumem_stats(fp, 2, 22)
        r_s = parse_cpumem_stats(fp_splice, 2, 22)
        r_e = parse_cpumem_stats(fp_emulated, 2, 21)
        r_s_e = parse_cpumem_stats(fp_emulated_splice, 2, 21)

        mem.append(r['mem'])
        cpu.append(r['%cpu'])
        mem_splice.append(r_s['mem'])
        cpu_splice.append(r_s['%cpu'])
        mem_emulated.append(r_e['mem'])
        cpu_emulated.append(r_e['%cpu'])
        mem_splice_emulated.append(r_s_e['mem'])
        cpu_splice_emulated.append(r_s_e['%cpu'])

    workload_cpu_chart(clients, cpu, cpu_splice, cpu_emulated, cpu_splice_emulated, 'cpu')
    workload_mem_chart(clients, mem, mem_splice, emulated=False, outfile='memory')
    workload_mem_chart(clients, mem_emulated, mem_splice_emulated, emulated=True, outfile='memory_emulated')


if __name__ == '__main__':
    parse_all_workload_data([1, 2, 4, 8, 16, 32, 64, 128, 256, 512])
