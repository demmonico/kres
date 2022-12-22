# kres

This is a Python script aimed to help monitor Kubernetes cluster utilisation and calculate utilisation and requests performance

## Installation

### Prerequisites

Make sure that you have:
- access to your Kubernetes cluster: `kubectl config current-context`
- `Python3` installed: `python --version` (consider `python3` when `python` points wrong)
- `pip` installed: `pip -V` (when it doesn't exist - `curl https://bootstrap.pypa.io/get-pip.py | python`)
- python dependencies installed `pip install -r requirements.txt` (consider `pip3` when `pip` points wrong)

### Setup

- clone this repo `git clone https://github.com/demmonico/kres.git && cd kres`

## Usage

Script usage
```shell
kres.py [-h|--help] [--kube-config-context KUBE_CONFIG_CONTEXT] [--kube-config-file KUBE_CONFIG_FILE] [--label-selector LABEL_SELECTOR]
               [--print-nodes] [-v|--verbose]
```

### Workflow

- select nodes from the selected (or default) context, labeled as `--label-selector` script argument (or all, when nothing were passed) 
- fetch current node utilisation from the node data
- traversing over all nodes, requesting node details to get the containers resource requests data, sum them up per node
- calculate statistics per cluster (see [this](#summary-output) section for details)

### Arguments

- `-h, --help` - show this help message and exit
- `--kube-config-context <KUBE_CONFIG_CONTEXT>, -c <KUBE_CONFIG_CONTEXT>` - a context name to work with. Optional, **the one from the kube config will be used by default if this parameter is not specified**
- `--kube-config-file <KUBE_CONFIG_FILE>, -f <KUBE_CONFIG_FILE>` - a config file to fetch cluster info from. Optional
- `--label-selector <LABEL_SELECTOR>, -s <LABEL_SELECTOR>` - a label selector to filter nodes to fetch data for. Optional, **empty by default**, means all nodes will be fetched
- `--print-nodes` - if specified, a table with node details gets printed as output. Optional flag, **disabled by default**
- `--verbose, -v` - enables verbose output mode. Optional flag, **disabled by default**

## Outputs

### Header output

Contains information about the current context, cluster, and the label selector applied

Example
```shell
KUBE_CLUSTER: staging // active context - qa (overwritten by script argument - staging)
LABEL_SELECTOR: application=example
```

### Summary output

Summary output contains 4 main cluster parameters (for CPU and RAM resources separately):
- **average utilisation**. It is calculated as the average of the resource utilisation over all selected nodes 
- **average requests**. It is calculated as the average of the resource requests over all selected nodes
- **requests performance**. It shows how well requests were defined considering the current level of utilisation. It is calculated as `(Av.%Req - Av.%Util) / Av.%Util * 100%`, where `Av.%Req` is the average of resource requests and `Av.%Util` is the average of resource utilisation over all selected nodes 

Example
```shell
Summary: (staging / application=example)
Cluster's CPU|RAM average UTILISATION        | CPU:   45.3% | RAM:   53.8%
Cluster's CPU|RAM average REQUESTS           | CPU:   42.5% | RAM:   37.8%
Cluster's CPU|RAM REQUESTS performance       | CPU:   -6.1% | RAM:  -29.7%
hint: (Av.%Req - Av.%Util) / Av.%Util * 100%
```

### One-line output

One-line output contains a one-line summary simplifying collecting and processing of historical stats:
- **utilisation / requests** (`CPU_U_R`, `RAM_U_R`). It shows the average of resource utilisation and the average of resource requests, resources are separated by `/`
- **requests performance** (`CPU_RU/U`, `RAM_RU/U`). It shows how well requests were defined considering the current level of utilisation. It is calculated as `(Av.%Req - Av.%Util) / Av.%Util * 100%`, where `Av.%Req` is the average of resource requests and `Av.%Util` is the average of resource utilisation over all selected nodes

Example
```shell
Cluster staging / application=example | CPU_U_R:  37.8% /   60.2% | CPU_RU/U:  59.4% | RAM_U_R:  51.6% /   50.6% | RAM_RU/U:  -2.1%
Cluster staging / application=example | CPU_U_R:  37.4% /   50.2% | CPU_RU/U:  34.5% | RAM_U_R:  52.7% /   46.2% | RAM_RU/U: -12.3%
Cluster staging / application=example | CPU_U_R:  40.9% /   43.8% | CPU_RU/U:   7.1% | RAM_U_R:  53.5% /   44.6% | RAM_RU/U: -16.7%
...
```

### Node details output

Node details output contains a table with cluster parameters (for CPU and RAM resources separately), calculated per each selected node:
- **allocated** (`CPU A`, `RAM A`). It shows the allocated amount of resources per node 
- **utilisation** (`CPU U (% U/A)`, `RAM U (% U/A)`). It shows the utilised amount of resources per node (absolute and relative values) 
- **requests** (`CPU R (% R/A)`, `RAM R (% R/A)`). It shows the requested resources per node (absolute and relative values) 
- **limits** (`CPU L (% L/A)`, `RAM L (% L/A)`). It shows the limits of resources per node (absolute and relative values) 
- **utilisation performance per requests**. It shows how well requests were defined considering the current level of utilisation. It is calculated as `%Util / %Req * 100%`, where `%Req` is the sum of resource requests and `%Util` is the sum of resource utilisation per node 
- **utilisation performance per limits**. It shows how well limits were defined considering the current level of utilisation. It is calculated as `%Util / %Lim * 100%`, where `%Lim` is the sum of resource limits and `%Util` is the sum of resource utilisation per node 

Just below it, there is also the footer containing following information:
- **total**. The sum of all absolute values of resources per node, e.g. **allocated**, **absolute utilisation**, etc
- **average**. The average of all relative values of resources per node, e.g. **absolute relative**, **relative requests**, etc

Example
```shell
Node                                         | CPU A | CPU U (% U/A)  | CPU R (% R/A)  |   CPU L (% L/A)   | %C U/R  | %C U/L  |  RAM A  |  RAM U (% U/A)   |  RAM R (% R/A)   |  RAM L (% L/A)   | %R U/R  | %R U/L
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ip-10-1-1-1.region.compute.internal          | 2000m |  703m /  35.1% |  665m /  33.2% |    5474m / 273.7% |  105.7% |   12.8% |  7733Mi |  4531Mi /  58.6% |  1761Mi /  22.8% |  4884Mi /  63.2% |  257.3% |   92.8%
ip-10-1-1-2.region.compute.internal          | 2000m | 1129m /  56.5% |  940m /  47.0% | 524360m /26218.0% |  120.1% |    0.2% |  7733Mi |  4790Mi /  61.9% |  3867Mi /  50.0% | 27340Mi / 353.5% |  123.9% |   17.5%
ip-10-1-1-3.region.compute.internal          | 2000m |  661m /  33.1% |  946m /  47.3% |   30594m /1529.7% |   69.9% |    2.2% |  7733Mi |  4586Mi /  59.3% |  3645Mi /  47.1% | 28436Mi / 367.7% |  125.8% |   16.1%
ip-10-1-1-4.region.compute.internal          | 2000m | 1130m /  56.5% |  851m /  42.5% |    8462m / 423.1% |  132.8% |   13.4% |  7733Mi |  2738Mi /  35.4% |  2433Mi /  31.5% |  9748Mi / 126.1% |  112.5% |   28.1%
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Total                                        | 8000m | 3623m /  45.3% | 3402m /  42.5% |  568890m /7111.1% |  106.5% |    0.6% | 30932Mi | 16645Mi /  53.8% | 11706Mi /  37.8% | 70408Mi / 227.6% |  142.2% |   23.6%
```

## Use cases

### Help

It shows the script's help

```shell
python3 kres.py --help
```

### General overview

Useful for a quick status check of your cluster 

```shell
# use current context from the kube config file
python3 kres.py --verbose
# OR
python3 kres.py -v
 
# use context staging
python3 kres.py -v -c staging
 
# will select only nodes labeled application=example
python3 kres.py -v -s application=example
```

Output

```shell
KUBE_CLUSTER: staging // active context - staging
LABEL_SELECTOR: application=example
 
Summary: (staging / application=example)
Cluster's CPU|RAM average UTILISATION        | CPU:   45.3% | RAM:   53.8%
Cluster's CPU|RAM average REQUESTS           | CPU:   42.5% | RAM:   37.8%
Cluster's CPU|RAM REQUESTS performance       | CPU:   -6.1% | RAM:  -29.7%
hint: (Av.%Req - Av.%Util) / Av.%Util * 100%
```

For understand the summary results better, please check [this](#summary-output) section.

### Detailed overview

Useful for a quick troubleshooting, when node details are important 

```shell
# select only nodes labeled application=example + it will also print node details table
python3 kres.py -v -s application=example --print-nodes
```

Output

```shell
KUBE_CLUSTER: staging // active context - staging
LABEL_SELECTOR: application=example

Node                                         | CPU A | CPU U (% U/A)  | CPU R (% R/A)  |   CPU L (% L/A)   | %C U/R  | %C U/L  |  RAM A  |  RAM U (% U/A)   |  RAM R (% R/A)   |  RAM L (% L/A)   | %R U/R  | %R U/L
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ip-10-1-1-1.region.compute.internal          | 2000m |  703m /  35.1% |  665m /  33.2% |    5474m / 273.7% |  105.7% |   12.8% |  7733Mi |  4531Mi /  58.6% |  1761Mi /  22.8% |  4884Mi /  63.2% |  257.3% |   92.8%
ip-10-1-1-2.region.compute.internal          | 2000m | 1129m /  56.5% |  940m /  47.0% | 524360m /26218.0% |  120.1% |    0.2% |  7733Mi |  4790Mi /  61.9% |  3867Mi /  50.0% | 27340Mi / 353.5% |  123.9% |   17.5%
ip-10-1-1-3.region.compute.internal          | 2000m |  661m /  33.1% |  946m /  47.3% |   30594m /1529.7% |   69.9% |    2.2% |  7733Mi |  4586Mi /  59.3% |  3645Mi /  47.1% | 28436Mi / 367.7% |  125.8% |   16.1%
ip-10-1-1-4.region.compute.internal          | 2000m | 1130m /  56.5% |  851m /  42.5% |    8462m / 423.1% |  132.8% |   13.4% |  7733Mi |  2738Mi /  35.4% |  2433Mi /  31.5% |  9748Mi / 126.1% |  112.5% |   28.1%
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Total                                        | 8000m | 3623m /  45.3% | 3402m /  42.5% |  568890m /7111.1% |  106.5% |    0.6% | 30932Mi | 16645Mi /  53.8% | 11706Mi /  37.8% | 70408Mi / 227.6% |  142.2% |   23.6%

Summary: (staging / application=example)
Cluster's CPU|RAM average UTILISATION        | CPU:   45.3% | RAM:   53.8%
Cluster's CPU|RAM average REQUESTS           | CPU:   42.5% | RAM:   37.8%
Cluster's CPU|RAM REQUESTS performance       | CPU:   -6.1% | RAM:  -29.7%
hint: (Av.%Req - Av.%Util) / Av.%Util * 100%
```

For understand the summary results better, please check [this](#summary-output) section.
For understand node details results better, please check [this](#node-details-output) section.

### Monitoring

Useful to gather cluster utilisation statistics over some time (instead of having a moment data, as described before). 

```shell
# select only nodes labeled application=example
watch -n 120 'python3 kres.py -s application=example >> logs/kres-staging-example.log'
 
# for monitoring multiple selectors at the same time
watch -n 180 'for label in common shared example; do python3 kres.py -s application=$label >> logs/kres-staging-$label.log; done'
```

**_Note: please, do not put too small interval for the watch util - it will overload your kube API server_**

Output

```shell
cat logs/kres-staging-example.log
Cluster staging / application=example | CPU_U_R:  37.8% /   60.2% | CPU_RU/U:  59.4% | RAM_U_R:  51.6% /   50.6% | RAM_RU/U:  -2.1%
Cluster staging / application=example | CPU_U_R:  37.4% /   50.2% | CPU_RU/U:  34.5% | RAM_U_R:  52.7% /   46.2% | RAM_RU/U: -12.3%
Cluster staging / application=example | CPU_U_R:  40.9% /   43.8% | CPU_RU/U:   7.1% | RAM_U_R:  53.5% /   44.6% | RAM_RU/U: -16.7%
...
```

For understand the one-line results better, please check [this](#one-line-output) section.

### Statistic calculating

Finally, to analyze collected data you can use [kres-stat](kres-stat.sh) helper.

Usage

```shell
./kres-stat.sh [ARGS|FLAGS]
```

Example

```shell
# simple run, when raw data were stored in a project's logs/ folder
./kres-stat.sh
 
# run with customised logs/ folder
./kres-stat.sh ~/logs-here
 
# run with customised logs/ folder and logs file mask
./kres-stat.sh ~/logs-here "*.txt"
```

Output

```shell
Mon Dec 19 17:34:59 CET 2022
/kres/logs/kres-staging-example.txt
Data samples       22
Metric / min / avg / stdev / max / p50 / p95
CPU_U/A 37.4 41.9045 3.03592 47.2 41.05 46.6
CPU_R/A 40.7 42.8864 4.33184 60.2 41.1 43.9
CPU_RU/U -13.4 3.26364 16.0447 59.4 0.3 11.5
RAM_U/A 51.6 52.9182 1.11626 55.4 52.7 55.1
RAM_R/A 43.7 44.7773 1.58571 50.6 44.3 46.2
RAM_RU/U -21.1 -15.3318 3.94086 -2.1 -16.3 -11.7
```

This output is space-separated, so it may simply be copied and pasted into any suitable tool to create visualisations or do data processing.
