# TCP Evaulation

## Mininet Testsuit

```bash
sudo apt-get install mininet
```

The execution of the mininet script requires root privileges.
```bash
usage: sudo run_mininet.py [-h] [-b BANDWIDTH] [-r RTT] [-d DIRECTORY]
                       [-s BUFFER_SIZE] [-l LATENCY] [-n NAME]
                       CONFIG

positional arguments:
  CONFIG          Path to the config file.

optional arguments:
  -h, --help      show this help message and exit
  -b BANDWIDTH    Initial bandwidth of the bottleneck link. (default: 10mbit)
  -r RTT          Initial rtt for all flows. (default 0ms)
  -d DIRECTORY    Path to the output directory. (default: .)
  -s BUFFER_SIZE  Burst size of the token bucket filter. (default: 1600b)
  -l LATENCY      Maximum latency at the bottleneck buffer. (default: 100ms)
  -n NAME         Name of the output directory. (default: TCP)
```

The configuration file is a text file formatted as follows

```
host, <algorithm>, <rtt>, <start>, <stop>
```
Add a new TCP stream using 'algorithm' for congestion control with 'rtt'.
The flow starts after 'start' seconds and ends 'stop' seconds afterwards.

```
link, <type>, <value>, <start>
```
Change the properties of the bottleneck link. The 'type' can either be bw for bandwidth or rtt for round-trip time.
The 'value' gives the new value for the link and 'start' sets the delay after which the change is applied. 

### Example
```
host, bbr, 40ms, 0, 40
host, cubic, 50ms, 5, 30
link, bw, 5mbit, 10
link, rtt, 100ms, 5
```
This config file results in the following test
```
0s  |   bbr flow, 40ms
    |        |
    |        |    
5s  |        |        cubic flow, 50ms
    |        |               |
    |        |               |
    |        |               |
    |        |               |
15s |  Set bottleneck bandwidth to 5mbit/s
    |        |               |
    |        |               |
20s |    Set bottleneck rtt to 100ms
    |        |               |
    |        |               |
    |        |               |
    |        |               |
    |        |               |
    |        |               |
35s |        |             stop
    |        |
40s |      stop
```

## Analysis 
The analysis script is called after the execution of the Mininet test and requires the target directory as parameter.
Eventually the permissions for the directory must be adjusted since they were created as root.
```bash
usage: analyze.py [-h] [-s {pcap,csv}] [-o {pdf+csv,pdf,csv}]
                        [-p1 PCAP1] [-p2 PCAP2] [-t DELTA_T] [-r] [-n]
                        PATH

positional arguments:
  PATH                  path to the working directory

optional arguments:
  -h, --help            show this help message and exit
  -s {pcap,csv}         Create plots from csv or pcap
  -o {pdf+csv,pdf,csv}  Output Format (default: pdf+csv)
  -p1 PCAP1             Filename of the pcap before the bottleneck (default:
                        s1.pcap)
  -p2 PCAP2             Filename of the pcap behind the bottleneck (default:
                        s3.pcap)
  -t DELTA_T            Interval in seconds for computing average
                        throughput,... (default: 0.2)
  -r                    Process all sub-directories recursively.
  -n                    Only process new (unprocessed) directories.
```