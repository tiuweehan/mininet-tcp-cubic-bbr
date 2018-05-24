import argparse
import dpkt
import socket
import os
import sys

from helper.csv_writer import write_to_csv, read_from_csv, CSV_PATH
from helper.pcap_data import PcapData, DataInfo
from helper.create_plots import plot_all, PLOT_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', metavar='PATH',
                        help='path to the working directory')
    parser.add_argument('-s', dest='source',
                        choices=['pcap', 'csv'],
                        default='pcap', help='Create plots from csv or pcap')
    parser.add_argument('-o', dest='output',
                        choices=['pdf+csv', 'pdf', 'csv'],
                        default='pdf+csv', help='Output Format (default: pdf+csv)')
    parser.add_argument('-p1', dest='pcap1',
                        default='s1.pcap', help='Filename of the pcap before the bottleneck '
                                                '(default: s1.pcap)')
    parser.add_argument('-p2', dest='pcap2',
                        default='s3.pcap', help='Filename of the pcap behind the bottleneck '
                                                '(default: s3.pcap)')
    parser.add_argument('-t', dest='delta_t',
                        default='0.2', help='Interval in seconds for computing average throughput,... '
                                            '(default: 0.2)')
    parser.add_argument('-r', dest='recursive', action='store_true',
                        help='Process all sub-directories recursively.')
    parser.add_argument('-n', dest='new', action='store_true',
                        help='Only process new (unprocessed) directories.')
    args = parser.parse_args()

    path = args.path

    paths = []

    if args.recursive:
        for subdirs, _, _ in os.walk(path):
            pcap1 = os.path.join(subdirs, args.pcap1)
            pcap2 = os.path.join(subdirs, args.pcap2)
            if os.path.isfile(pcap1) and os.path.isfile(pcap2):
                unprocessed = True
                if args.new:
                    csv_path = os.path.join(subdirs, CSV_PATH)
                    pdf_path = os.path.join(subdirs, PLOT_PATH)
                    unprocessed = not os.path.exists(csv_path) or not os.path.exists(pdf_path)
                if unprocessed:
                    paths.append(subdirs)
        print('Found {} pcaps in sub directories.'.format(len(paths)))
    else:
        paths = [path]

    paths = sorted(paths)

    for i, path in enumerate(paths):

        if args.source is 'pcap':
            if not os.path.isfile(os.path.join(path, args.pcap1)):
                print("File not found: {}".format(os.path.join(path, args.pcap1)))
                return
            if not os.path.isfile(os.path.join(path, args.pcap2)):
                print("File not found: {}".format(os.path.join(path, args.pcap2)))
                return

            print('{}/{} Reading pcap {}'.format(i + 1, len(paths), path))
            pcap_data = parse_pcap(path=path,
                                   pcap_file1=args.pcap1,
                                   pcap_file2=args.pcap2,
                                   delta_t=float(args.delta_t))

            if 'csv' in args.output:
                print('Writing to csv ...')
                write_to_csv(path, pcap_data)
        else:
            print('{}/{} Reading csv {}'.format(i + 1, len(paths), path))
            pcap_data = read_from_csv(path)
            if pcap_data == -1:
                continue

        if 'pdf' in args.output:
            print('Creating plots ...')
            plot_all(path, pcap_data)


def parse_pcap(path, pcap_file1, pcap_file2, delta_t):
    file_name1 = os.path.join(path, pcap_file1)
    file_name2 = os.path.join(path, pcap_file2)

    print("Processing: {}".format(path))

    files_exist = True
    for f in [file_name1, file_name2]:
        if os.path.isfile(f):
            pass
        else:
            print("File Missing: {}".format(f))
            files_exist = False

    if not files_exist:
        sys.exit(-1)

    f = open(file_name1)
    pcap = dpkt.pcap.Reader(f)

    connections = []
    active_connections = []

    round_trips = {}
    inflight = {}
    sending_rate = {}
    avg_rtt = {}

    inflight_seq = {}
    inflight_ack = {}

    sending_rate_data_size = {}

    inflight_avg = {}

    avg_rtt_samples = {}

    total_throughput = ([], [])
    total_sending_rate = ([], [])

    retransmissions = {}
    retransmission_counter = {}
    packet_counter = {}
    retransmissions_interval = {}
    total_retransmisions = ([], [], [])

    start_seq = {}

    t = 0

    ts_vals = {}
    seqs = {}

    start_ts = -1

    print('Connections:')
    for ts, buf in pcap:
        if start_ts < 0:
            start_ts = ts

        eth = dpkt.ethernet.Ethernet(buf)
        ip = eth.data
        tcp = ip.data

        src_ip = socket.inet_ntoa(ip.src)
        dst_ip = socket.inet_ntoa(ip.dst)
        src_port = tcp.sport
        dst_port = tcp.dport

        # identify a connection always as (client port, server port)
        if src_port > dst_port:
            tcp_tuple = (src_ip, src_port, dst_ip, dst_port)
        else:
            tcp_tuple = (dst_ip, dst_port, src_ip, src_port)

        if tcp.flags & 0x01:
            if tcp_tuple in active_connections:
                active_connections.remove(tcp_tuple)
                print('  [FIN] {}:{} -> {}:{}'.format(tcp_tuple[0], tcp_tuple[1],
                                                      tcp_tuple[2], tcp_tuple[3]))
            continue

        if tcp.flags & 0x02 and tcp_tuple not in connections:
            connections.append(tcp_tuple)
            active_connections.append(tcp_tuple)
            connection_index = connections.index(tcp_tuple)

            start_seq[connection_index] = tcp.seq

            round_trips[connection_index] = ([], [])
            inflight[connection_index] = ([], [])
            avg_rtt[connection_index] = ([], [])
            sending_rate[connection_index] = ([], [])

            ts_vals[connection_index] = ([], [])
            seqs[connection_index] = []

            inflight_seq[connection_index] = 0
            inflight_ack[connection_index] = 0

            inflight_avg[connection_index] = []

            sending_rate_data_size[connection_index] = 0

            avg_rtt_samples[connection_index] = []

            retransmissions[connection_index] = ([],)
            retransmission_counter[connection_index] = 0
            packet_counter[connection_index] = 0
            retransmissions_interval[connection_index] = ([], [], [])

            print('  [SYN] {}:{} -> {}:{}'.format(tcp_tuple[0], tcp_tuple[1],
                                                  tcp_tuple[2], tcp_tuple[3]))
            continue

        if ts - start_ts > t:

            total_sending_rate[0].append(t)
            total_sending_rate[1].append(0)

            total_retransmisions[0].append(t)
            total_retransmisions[1].append(0)
            total_retransmisions[2].append(0)

            for i, c in enumerate(connections):

                if c not in active_connections:
                    continue

                tp = float(sending_rate_data_size[i]) / delta_t
                sending_rate[i][0].append(t)
                sending_rate[i][1].append(tp)
                sending_rate_data_size[i] = 0

                total_sending_rate[1][-1] += tp

                retransmissions_interval[i][0].append(t)
                retransmissions_interval[i][1].append(retransmission_counter[i])
                retransmissions_interval[i][2].append(packet_counter[i])
                total_retransmisions[1][-1] += retransmission_counter[i]
                total_retransmisions[2][-1] += packet_counter[i]
                retransmission_counter[i] = 0
                packet_counter[i] = 0

                inflight[i][0].append(t)
                if len(inflight_avg[i]) > 0:
                    inflight[i][1].append(sum(inflight_avg[i]) / len(inflight_avg[i]))
                else:
                    inflight[i][1].append(inflight_seq[connection_index] - inflight_ack[connection_index])
                inflight_avg[i] = []

                if len(avg_rtt_samples[i]) > 0:
                    avg_rt = sum(avg_rtt_samples[i]) / len(avg_rtt_samples[i])
                    avg_rtt[i][0].append(t)
                    avg_rtt[i][1].append(avg_rt)
                avg_rtt_samples[i] = []

            t += delta_t

        connection_index = connections.index(tcp_tuple)

        ts_val = None
        ts_ecr = None

        options = dpkt.tcp.parse_opts(tcp.opts)
        for opt in options:
            if opt[0] == dpkt.tcp.TCP_OPT_TIMESTAMP:
                ts_val = reduce(lambda x, r: (x << 8) + r, map(ord, opt[1][:4]))
                ts_ecr = reduce(lambda x, r: (x << 8) + r, map(ord, opt[1][4:]))

        if src_port > dst_port:
            # client -> server
            tcp_seq = tcp.seq - start_seq[connection_index]
            if tcp_seq < 0:
                tcp_seq += 2 ** 32

            inflight_seq[connection_index] = max(tcp_seq, inflight_seq[connection_index])
            sending_rate_data_size[connection_index] += ip.len * 8

            if tcp_seq in seqs[connection_index]:
                retransmissions[connection_index][0].append(ts - start_ts)
                retransmission_counter[connection_index] += 1

            else:
                packet_counter[connection_index] += 1
                if len(tcp.data) > 0:
                    seqs[connection_index].append(tcp_seq)
                if ts_val is not None:
                    ts_vals[connection_index][0].append(ts)
                    ts_vals[connection_index][1].append(ts_val)

        else:
            # server -> client
            tcp_ack = tcp.ack - start_seq[connection_index]
            if tcp_ack < 0:
                tcp_ack += 2 ** 32

            inflight_ack[connection_index] = max(tcp_ack, inflight_ack[connection_index])

            seqs[connection_index] = [x for x in seqs[connection_index] if x >= tcp_ack]

            if ts_ecr in ts_vals[connection_index][1]:
                index = ts_vals[connection_index][1].index(ts_ecr)
                rtt = (ts - ts_vals[connection_index][0][index]) * 1000

                ts_vals[connection_index][0].pop(index)
                ts_vals[connection_index][1].pop(index)

                avg_rtt_samples[connection_index].append(rtt)

                round_trips[connection_index][0].append(ts - start_ts)
                round_trips[connection_index][1].append(rtt)

        inflight_data = inflight_seq[connection_index] - inflight_ack[connection_index]
        inflight_avg[connection_index].append(inflight_data * 8)

    f.close()

    # Compute throughput after the bottleneck
    f = open(file_name2)
    pcap = dpkt.pcap.Reader(f)

    connections = []
    active_connections = []
    throughput = {}

    throughput_data_size = {}

    start_ts = -1
    t = 0

    for ts, buf in pcap:

        if start_ts < 0:
            start_ts = ts

        eth = dpkt.ethernet.Ethernet(buf)
        ip = eth.data
        tcp = ip.data

        src_ip = socket.inet_ntoa(ip.src)
        dst_ip = socket.inet_ntoa(ip.dst)
        src_port = tcp.sport
        dst_port = tcp.dport

        # identify a connection always as (client port, server port)
        if src_port > dst_port:
            tcp_tuple = (src_ip, src_port, dst_ip, dst_port)
        else:
            tcp_tuple = (dst_ip, dst_port, src_ip, src_port)

        if tcp.flags & 0x01:
            if tcp_tuple in active_connections:
                active_connections.remove(tcp_tuple)
            continue

        if tcp.flags & 0x02 and tcp_tuple not in connections:
            connections.append(tcp_tuple)
            active_connections.append(tcp_tuple)
            connection_index = connections.index(tcp_tuple)

            throughput[connection_index] = ([], [])
            throughput_data_size[connection_index] = 0
            continue

        if ts - start_ts > t:
            total_throughput[0].append(t)
            total_throughput[1].append(0)

            for i, c in enumerate(connections):
                if c not in active_connections:
                    continue
                tp = float(throughput_data_size[i]) / delta_t
                throughput[i][0].append(t)
                throughput[i][1].append(tp)
                total_throughput[1][-1] += tp
                throughput_data_size[i] = 0
            t += delta_t

        connection_index = connections.index(tcp_tuple)

        if src_port > dst_port:
            # client -> server
            throughput_data_size[connection_index] += ip.len * 8

    fairness_troughput = compute_fairness(throughput)
    fairness_sending_rate = compute_fairness(sending_rate)
    fairness = {
        'Throughtput': fairness_troughput,
        'Sending Rate': fairness_sending_rate
    }

    bbr_values, cwnd_values = parse_bbr_and_cwnd_values(path)
    bbr_total_values, sync_phases, sync_duration = compute_total_values(bbr_values)
    buffer_backlog = parse_buffer_backlog(path)

    data_info = DataInfo(sync_duration=sync_duration,
                         sync_phases=sync_phases)

    throughput[len(throughput)] = total_throughput
    sending_rate[len(sending_rate)] = total_sending_rate
    retransmissions_interval[len(retransmissions_interval)] = total_retransmisions

    return PcapData(rtt=round_trips,
                    inflight=inflight,
                    throughput=throughput,
                    fairness=fairness,
                    avg_rtt=avg_rtt,
                    sending_rate=sending_rate,
                    bbr_values=bbr_values,
                    bbr_total_values=bbr_total_values,
                    cwnd_values=cwnd_values,
                    retransmissions=retransmissions,
                    retransmissions_interval=retransmissions_interval,
                    buffer_backlog=buffer_backlog,
                    data_info=data_info)


def parse_buffer_backlog(path):
    output = {}
    paths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.buffer')]

    for i, p in enumerate(paths):
        output[i] = ([], [])
        f = open(p)
        for line in f:
            split = line.split(' ')
            timestamp = parse_timestamp(split[0])
            size = split[2].replace('b\n', '')
            if 'K' in size:
                size = float(size.replace('K', '')) * 1000
            elif 'M' in size:
                size = float(size.replace('M', '')) * 1000000
            elif 'G' in size:
                size = float(size.replace('G', '')) * 1000000000
            output[i][0].append(timestamp)
            output[i][1].append(float(size) * 8)
        f.close()
    return output


def parse_bbr_and_cwnd_values(path):
    files = []
    bbr_values = {}
    cwnd_values = {}

    all_files = os.listdir(path)
    all_files = [f for f in all_files if f.endswith(".bbr")]
    all_files = sorted(all_files)

    for i, f in enumerate(all_files):
        files.append(os.path.join(path, f))
        bbr_values[i] = ([], [], [], [], [], [])
        cwnd_values[i] = ([], [], [])

    for i, file_path in enumerate(files):
        f = open(file_path)

        for line in f:
            split = line.split(';')
            split = map(lambda x: x.strip(), split)
            timestamp = parse_timestamp(split[0])

            if split[1] != '':
                bbr = split[1].replace('bbr:(', '').replace(')\n', '')\
                    .replace('bw:', '').replace('mrtt:','').replace('pacing_gain:', '').replace('cwnd_gain:', '')
                bbr = bbr.split(',')

                if len(bbr) < 4:
                    pacing_gain = 0
                    cwnd_gain = 0
                else:
                    pacing_gain = float(bbr[2])
                    cwnd_gain = float(bbr[3])

                if 'Mbps' in bbr[0]:
                    bw = float(bbr[0].replace('Mbps', '')) * 1000000
                elif 'Kbps' in bbr[0]:
                    bw = float(bbr[0].replace('Kbps', '')) * 1000
                elif 'bps' in bbr[0]:
                    bw = float(bbr[0].replace('bps', ''))
                else:
                    bw = 0

                rtt = float(bbr[1])

                bbr_values[i][0].append(timestamp)
                bbr_values[i][1].append(bw)
                bbr_values[i][2].append(rtt)
                bbr_values[i][3].append(pacing_gain)
                bbr_values[i][4].append(cwnd_gain)
                bbr_values[i][5].append(bw * rtt / 1000)

            cwnd = 0
            ssthresh = 0

            if len(split) < 4:
                continue

            if split[2] != '':
                cwnd = int(split[2].replace('cwnd:', ''))
            if split[3] != '':
                ssthresh = int(split[3].replace('ssthresh:', ''))

            cwnd_values[i][0].append(timestamp)
            cwnd_values[i][1].append(cwnd)
            cwnd_values[i][2].append(ssthresh)

        f.close()
    return bbr_values, cwnd_values


def parse_timestamp(string):
    seconds = 0
    string = string.split(':')
    seconds += float(string[0]) * 3600
    seconds += float(string[1]) * 60
    seconds += float(string[2])
    return seconds


def compute_total_values(bbr):
    connection_first_index = [0, ] * len(bbr)
    current_bw = [0, ] * len(bbr)
    current_window = [0, ] * len(bbr)
    current_gain = [0, ] * len(bbr)
    total_bw = ([], [])
    total_window = ([], [])
    total_gain = ([], [])

    sync_window_start = -1
    sync_window_phases = []
    sync_window_durations = []
    print("Synchron Probe RTT:")

    while True:
        active_connections = 0
        current_timestamps = {}

        for c in bbr:
            if connection_first_index[c] < len(bbr[c][0]):
                current_timestamps[c] = bbr[c][0][connection_first_index[c]]
                active_connections += 1
            else:
                current_window[c] = 0
                current_bw[c] = 0
                current_gain[c] = 0

        if active_connections < 1:
            break

        c, ts = min(current_timestamps.items(), key=lambda x: x[1])
        current_bw[c] = bbr[c][1][connection_first_index[c]]
        current_window[c] = float(bbr[c][4][connection_first_index[c]])
        current_gain[c] = float(bbr[c][3][connection_first_index[c]])
        connection_first_index[c] += 1

        total_bw[0].append(ts)
        total_bw[1].append(sum(current_bw))

        total_window[0].append(ts)
        total_window[1].append(sum(current_window))

        total_gain[0].append(ts)
        total_gain[1].append(sum(current_gain))

        min_window = 0
        for i in connection_first_index:
            if i > 0:
                min_window += 1

        if sum(current_window) == min_window:
            if sync_window_start < 0:
                sync_window_start = ts
                sync_window_phases.append(sync_window_start)
        elif sync_window_start > 0:
            duration = (ts - sync_window_start) * 1000
            sync_window_start = -1
            sync_window_durations.append(duration)

    return {0: total_bw, 1: total_window, 2: total_gain}, sync_window_phases, sync_window_durations


def compute_fairness(data):
    output = ([], [])
    connections = []
    timestamps = []

    for c in data:
        if len(timestamps) < len(data[c][0]):
            timestamps = data[c][0]
        connections.append(data[c])

    for i, ts in enumerate(timestamps):
        sum_normal = 0.0
        active_connections = 0
        sum_square = 0.0
        for c in connections:
            v = -1
            for index, value in enumerate(c[0]):
                if ts == value:
                    v = index
            if v < 0:
                continue

            active_connections += 1
            sum_normal += c[1][v]
            sum_square += c[1][v] ** 2
        if sum_square == 0:
            continue
        jain_index = sum_normal ** 2 / (active_connections * sum_square)
        output[0].append(ts)
        output[1].append(jain_index)

    return output


if __name__ == "__main__":
    main()
