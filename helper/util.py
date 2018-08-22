import subprocess
import time
import sys


def print_error(line):
    print('\x1b[1;31;40m{}\x1b[0m'.format(line))


def print_warning(line):
    print('\x1b[1;33;40m{}\x1b[0m'.format(line))


def print_success(line):
    print('\x1b[1;32;40m{}\x1b[0m'.format(line))


def get_git_revision_hash():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.PIPE).rstrip()
    except subprocess.CalledProcessError as e:
        print_error(e)
        return 'unknown'


def get_host_version():
    try:
        return subprocess.check_output(['uname', '-ovr'], stderr=subprocess.PIPE).rstrip()
    except subprocess.CalledProcessError as e:
        print_error(e)
        return 'unknown'


def get_available_algorithms():
    try:
        return subprocess.check_output(['sysctl net.ipv4.tcp_available_congestion_control '
                                        '| sed -ne "s/[^=]* = \(.*\)/\\1/p"'], shell=True)
    except subprocess.CalledProcessError as e:
        print_error('Cannot retrieve available congestion control algorithms.')
        print_error(e)
        return ''


def check_tools():
    missing_tools = []
    tools = {
        'tcpdump': 'tcpdump',
        'ethtool': 'ethtool',
        'netcat': 'netcat',
        'moreutils': 'ts'
    }

    for package, tool in tools.items():
        try:
            process = subprocess.Popen(['which', tool], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = process.communicate()[0]
            if out == "":
                missing_tools.append(package)
        except (OSError, subprocess.CalledProcessError) as e:
            missing_tools.append(package)

    if len(missing_tools) > 0:
        print_error('Missing tools. Please run')
        print_error('  apt install ' + ' '.join(missing_tools))

    return len(missing_tools)


def print_timer(complete, current):
    share = current * 100.0 / complete

    string = '  {:6.2f}%'.format(share)
    if complete == current:
        string = '\x1b[1;32;40m' + string + '\x1b[0m'

    string += ' ['
    string += '=' * int(share / 10 * 3)
    string += ' ' * (30 - int(share / 10 * 3))
    string += '] {:6.1f}s remaining'.format(complete - current)

    if complete != current:
        string += '\r'
    else:
        string += '\n'

    sys.stdout.write(string)
    sys.stdout.flush()


def sleep_progress_bar(seconds, current_time, complete):
    print_timer(complete=complete, current=current_time)
    while seconds > 0:
        time.sleep(min(1, seconds))
        current_time = current_time + min(1, seconds)
        print_timer(complete=complete, current=current_time)
        seconds -= 1
    return current_time
