import numpy as np
import os
import errno
import math

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

PLOT_PATH = 'pdf_plots'

PLOT_TOTAL = True


PLOT_TYPES = [
    'sending_rate',
    'throughput',
    'fairness',
    'retransmissions',
    'avg_rtt',
    'rtt',
    'inflight',
    'cwnd',
    'buffer_backlog',
    'bdp',
    'btl_bw',
    'rt_prop',
    'window_gain',
    'pacing_gain',
]


class Plot:
    def __init__(self, data, plot_function, file_name, plot_name, unit):
        self.data = data
        self.plot_function = plot_function
        self.file_name = file_name
        self.plot_name = plot_name
        self.unit = unit


def plot_all(path, pcap_data, plot_only, hide_total=False, skip_retransmission=False):

    global PLOT_TOTAL
    PLOT_TOTAL = not hide_total

    path = os.path.join(path, PLOT_PATH)

    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    throughput = pcap_data.throughput
    fairness = pcap_data.fairness
    rtt = pcap_data.rtt
    inflight = pcap_data.inflight
    avg_rtt = pcap_data.avg_rtt
    sending_rate = pcap_data.sending_rate
    bbr_values = pcap_data.bbr_values
    bbr_total_values = pcap_data.bbr_total_values
    cwnd_values = pcap_data.cwnd_values
    retransmissions = pcap_data.retransmissions
    retransmissions_interval = pcap_data.retransmissions_interval
    buffer_backlog = pcap_data.buffer_backlog

    t_max = 0
    for t in throughput:
        t_max = max(t_max, throughput[t][0][-1])

    plots = []

    if 'sending_rate' in plot_only:
        plots += [
            Plot((sending_rate, retransmissions), plot_sending_rate, 'plot_sending_rate.pdf', 'Sending Rate', 'bit/s')
        ]

    if 'throughput' in plot_only:
        plots += [
            Plot((throughput, retransmissions), plot_throughput, 'plot_throughput.pdf', 'Throughput', 'bit/s')
        ]

    if 'fairness' in plot_only and len(sending_rate.keys()) > 2:
        plots += [
            Plot(fairness, plot_fairness, 'plot_fairness.pdf', 'Fairness', "Jain's Index")
        ]

    if 'retransmissions' in plot_only and not skip_retransmission:
        plots += [
            Plot(retransmissions_interval, plot_retransmissions, 'plot_retransmissions.pdf', 'Retransmissions', '#'),
            #Plot(retransmissions_interval, plot_retransmission_rate, 'plot_retransmission_rate.pdf', 'Retransmission Rate', '%'),
        ]

    if 'avg_rtt' in plot_only:
        plots += [
            Plot(avg_rtt, plot_avg_rtt, 'plot_avg_rtt.pdf', 'Avg RTT', 'ms')
        ]

    if 'rtt' in plot_only:
        plots += [
            Plot(rtt, plot_rtt, 'plot_rtt.pdf', 'RTT', 'ms')
        ]

    if 'inflight' in plot_only:
        plots += [
            Plot(inflight, plot_inflight, 'plot_inflight.pdf', 'Inflight', 'bit')
        ]

    if 'cwnd' in plot_only:
        plots += [
            Plot(cwnd_values, plot_cwnd, 'plot_cwnd.pdf', 'CWND', 'MSS')
        ]

    if 'buffer_backlog' in plot_only and len(buffer_backlog) > 0:
        plots += [
            Plot((buffer_backlog, retransmissions), plot_buffer_backlog, 'plot_buffer_backlog.pdf', 'Buffer Backlog', 'bit')
        ]

    has_bbr = False
    for i in bbr_values:
        if len(bbr_values[i][0]) > 0:
            has_bbr = True
            break

    if 'bdp' in plot_only and has_bbr:
        plots += [
            Plot(bbr_values, plot_bbr_bdp, 'plot_bbr_bdp.pdf', 'BDP', 'bit'),
            # Plot((inflight, bbr_values), plot_diff_inflight_bdp, 'plot_inflight_div_bdp.pdf', 'Inflight/BDP', ''),
        ]

    if 'btl_bw' in plot_only and has_bbr:
        plots += [
            Plot((bbr_values, bbr_total_values), plot_bbr_bw, 'plot_bbr_bw.pdf', 'btl_bw', 'bit/s'),
        ]

    if 'rt_prop' in plot_only and has_bbr:
        plots += [
            Plot(bbr_values, plot_bbr_rtt, 'plot_bbr_rtt.pdf', 'rt_prop', 'ms'),
        ]

    if 'window_gain' in plot_only and has_bbr:
        plots += [
            Plot((bbr_values, bbr_total_values), plot_bbr_window, 'plot_bbr_window.pdf', 'Window Gain', ''),
        ]

    if 'pacing_gain' in plot_only and has_bbr:
        plots += [
            Plot((bbr_values, bbr_total_values), plot_bbr_pacing, 'plot_bbr_pacing.pdf', 'Pacing Gain', '')
        ]

    grid_tick_maior_interval = 10
    grid_tick_minor_interval = 2
    grid_tick_max_value = sending_rate[len(sending_rate) - 1][0][-1]
    """
    for plot in plots:
        f, ax = plt.subplots(1)
        f.set_size_inches(20, 10)

        ax.set_xticks(np.arange(0, grid_tick_max_value, grid_tick_maior_interval))
        ax.set_xticks(np.arange(0, grid_tick_max_value, grid_tick_minor_interval), minor=True)
        ax.grid(which='both', color='black', linestyle='dashed', alpha=0.4)
        plot[1](plot[0], ax)
        f.tight_layout()

        plt.savefig(os.path.join(path, plot[2]))
        plt.close()
        print("  *  {} created".format(plot[2]))
        """
    f, axarr = plt.subplots(len(plots), sharex=True)

    if len(plots) == 1:
        axarr = [axarr]

    pdf_height = 55.0 * float(len(plots)) / len(PLOT_TYPES)
    f.set_size_inches(20, pdf_height)

    print("  *  create plot_complete.pdf")
    for i, plot in enumerate(plots):
        axarr[i].set_xticks(np.arange(0, grid_tick_max_value, grid_tick_maior_interval))
        axarr[i].set_xticks(np.arange(0, grid_tick_max_value, grid_tick_minor_interval), minor=True)
        axarr[i].grid(b=True, which='major', color='black', linestyle='dashed', alpha=0.2, linewidth=1.5)
        axarr[i].grid(b=True, which='minor', color='black', linestyle='dashed', alpha=0.2)


        label = plot.plot_name
        if plot.unit != '':
            label += ' in {}'.format(plot.unit)

        axarr[i].set_ylabel(label)
        axarr[i].set_title('{}. {}'.format(i, plot.plot_name))
        plot.plot_function(plot.data, axarr[i])
        axarr[i].set_xlim(xmax=t_max)
        print("     -  {} created".format(plot.plot_name))

    f.tight_layout()
    plt.savefig(os.path.join(path, 'plot_complete.pdf'))
    plt.close()


def plot_throughput(data, p_plt):
    throughput = data[0]
    retransmissions = data[1]
    total = len(throughput) - 1

    if total > 1 and PLOT_TOTAL:
        data = throughput[total]
        data = filter_smooth(data, 5, 2)
        p_plt.plot(data[0], data[1], label='Total Throughput', color='#444444')

    for c in throughput:
        data = throughput[c]
        data = filter_smooth(data, 5, 2)

        if int(c) != total:
            p_plt.plot(data[0], data[1], label='Connection {}'.format(c))

    for c in retransmissions:
        data = retransmissions[c]
        p_plt.plot(data, np.zeros_like(data), '.', color='red')


def plot_sending_rate(data, p_plt):
    sending_rate = data[0]
    retransmissions = data[1]
    total = len(sending_rate) - 1

    if total > 1 and PLOT_TOTAL:
        data = sending_rate[total]
        data = filter_smooth(data, 5, 2)
        p_plt.plot(data[0], data[1], label='Total Sending Rate', color='#444444')

    for c in sending_rate:
        data = sending_rate[c]
        data = filter_smooth(data, 5, 2)

        if int(c) != total:
            p_plt.plot(data[0], data[1], label='Connection {}'.format(c))

    for c in retransmissions:
        data = retransmissions[c]
        p_plt.plot(data, np.zeros_like(data), '.', color='red')


def plot_fairness(fairness, p_plt):
    for c in fairness:
        data = filter_smooth((fairness[c][0], fairness[c][1]), 10, 2)
        p_plt.plot(data[0], data[1], label=c)

    p_plt.set_ylim(ymin=0, ymax=1.1)
    p_plt.legend()


def plot_rtt(rtt, p_plt):
    for c in rtt:
        data = rtt[c]
        p_plt.plot(data[0], data[1], label='Connection {}'.format(c))
    p_plt.set_ylim(ymin=0)


def plot_avg_rtt(avg_rtt, p_plt):
    for c in avg_rtt:
        data = avg_rtt[c]
        data = filter_smooth(data, 3, 2)
        p_plt.plot(data[0], data[1], label='Connection {}'.format(c))
    p_plt.set_ylim(ymin=0)


def plot_inflight(inflight, p_plt):
    for c in inflight:
        data = inflight[c]
        data = filter_smooth(data, 5, 1)
        p_plt.plot(data[0], data[1], label='Connection {}'.format(c))


def plot_buffer_backlog(data, p_plt):
    buffer_backlog = data[0]
    retransmissions = data[1]
    for c in buffer_backlog:
        data = buffer_backlog[c]

        if len(data[0]) < 1:
            continue
        data = filter_smooth(data, 5, 2)
        p_plt.plot(data[0], data[1], label='Buffer Backlog {}'.format(c))

    for c in retransmissions:
        data = retransmissions[c]
        p_plt.plot(data, np.zeros_like(data), '.', color='red')


def plot_bbr_bw(data, p_plt):
    bbr = data[0]
    bbr_bw_total = data[1]

    num_flows = 0
    for c in bbr:
        data = bbr[c]
        p_plt.plot(data[0], data[1], label='Connection {}'.format(c))
        if len(data[0]) > 0:
            num_flows += 1

    if len(bbr) > 2 and num_flows > 1 and PLOT_TOTAL:
        p_plt.plot(bbr_bw_total[0][0], bbr_bw_total[0][1], label='Total', color='#444444')
    p_plt.legend()


def plot_bbr_rtt(bbr, p_plt):
    for c in bbr:
        data = bbr[c]
        p_plt.plot(data[0], data[2], label='Connection {}'.format(c))


def plot_bbr_pacing(data, p_plt):
    bbr, total = data
    for c in bbr:
        data = bbr[c]
        p_plt.plot(data[0], data[3], label='Connection {}'.format(c))
    #if len(bbr) > 1:
    #    p_plt.plot(total[2][0], total[2][1], label='Total', color='#444444')
    p_plt.legend()


def plot_bbr_window(data, p_plt):
    bbr, total = data
    num_flows = 0
    for c in bbr:
        data = bbr[c]
        p_plt.plot(data[0], data[4], label='Connection {}'.format(c))
        if len(data[0]) > 0:
            num_flows += 1
    if len(bbr) > 2 and num_flows > 1 and PLOT_TOTAL:
        p_plt.plot(total[1][0], total[1][1], label='Total', color='#444444')
    p_plt.legend()


def plot_bbr_bdp(bbr, p_plt):
    for c in bbr:
        data = bbr[c]
        p_plt.plot(data[0], data[5], label='Connection {}'.format(c))


def plot_cwnd(cwnd, p_plt):
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    p_plt.plot([], [], label='CWND', color='black')
    p_plt.plot([], [], ':', label='SSTHRES', color='black')
    p_plt.legend()

    for i, c in enumerate(cwnd):
        data = cwnd[c]
        p_plt.plot(data[0], data[1], color=colors[i % len(colors)])
        p_plt.plot(data[0], data[2], ':', color=colors[i % len(colors)])


def plot_retransmissions(ret_interval, p_plt):
    plot_sum = (ret_interval[len(ret_interval) - 1][0][:],
                ret_interval[len(ret_interval) - 1][1][:])
    total_sum = 0
    for c in ret_interval:

        if c is len(ret_interval) - 1:
            continue

        data = ret_interval[c]
        total_loss = int(sum(data[1]))
        total_sum += total_loss
        p_plt.bar(plot_sum[0], plot_sum[1], plot_sum[0][1], label=total_loss)
        for i, value in enumerate(data[0]):
            if value in plot_sum[0]:
                plot_sum[1][plot_sum[0].index(value)] -= data[1][i]

    p_plt.bar(plot_sum[0], plot_sum[1], plot_sum[0][1], label='Total {}'.format(total_sum), color='black')
    p_plt.legend()


def plot_retransmission_rate(ret_interval, p_plt):
    data = ret_interval[len(ret_interval) - 1]

    rate = []
    ts = data[0]

    for i,_ in enumerate(data[1]):
        if data[2][i] == 0:
            rate.append(0)
        else:
            rate.append(float(data[1][i]) / float(data[2][i]) * 100)
    p_plt.plot(ts, rate, label='Retransmission Rate')
    p_plt.set_ylim(ymin=0)


def plot_diff_inflight_bdp(data, p_plt):
    inflight = data[0]
    bbr = data[1]
    for c in inflight:

        if c not in bbr:
            continue

        ts = []
        diff = []

        bbr_ts = bbr[c][0]
        bdp = bbr[c][5]

        for i, t1 in enumerate(inflight[c][0]):
            for j, t2 in enumerate(bbr_ts):
                if t1 > t2:
                    ts.append(t2)
                    if bdp[j] == 0:
                        diff.append(0)
                    else:
                        diff.append((inflight[c][1][i]) / bdp[j])
                else:
                    bbr_ts = bbr_ts[j:]
                    bdp = bdp[j:]
                    break
        ts, diff = filter_smooth((ts, diff), 10, 5)
        p_plt.plot(ts, diff, label='Connection {}'.format(c))


def filter_smooth(data, size, repeat=1):
    x = data[0]
    y = data[1]

    if repeat == 0:
        return x, y

    size = int(math.ceil(size / 2.0))
    for _ in range(1, repeat):
        y_smooth = []
        for i in range(0, len(y)):
            avg = 0
            avg_counter = 0
            for j in range(max(0, i - size), min(i + size, len(y) - 1)):
                avg += y[j]
                avg_counter += 1
            if avg_counter > 0:
                y_smooth.append(avg / avg_counter)
            else:
                y_smooth.append(0)
        y = y_smooth
    return x, y


def filter_percentile(data, percentile_min=0.0, percentile_max=0.0):
    min_size = int(math.floor(percentile_min * len(data[0])))
    max_size = int(math.floor(percentile_max * len(data[0])))

    y, x = zip(*sorted(zip(data[1], data[0])))
    if max_size > 0:
        x = x[min_size:-max_size]
        y = y[min_size:-max_size]
    else:
        x = x[min_size:]
        y = y[min_size:]

    x, y = zip(*sorted(zip(x, y)))

    return x, y
