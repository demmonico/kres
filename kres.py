#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This is a Python script aimed to help monitor Kubernetes cluster utilisation and resource request performance across its nodes
   Check README.md for usage examples

   FORMAT: python3 kres.py [ARGS|FLAGS]

   @author: https://github.com/demmonico
   @package: https://github.com/demmonico/kres
"""

import argparse, sys    # args
from kubernetes import client, config
import re               # for Converter


class Converter:
  def cpu_as_milicores(value):
    if re.match(r"[0-9]{1,9}m", str(value)):
      cpu = re.sub("[^0-9]", "", value)
    elif re.match(r"[0-9]{1,4}$", str(value)):
      cpu = int(value) * 1000
    elif re.match(r"[0-9]{1,15}n", str(value)):
      cpu = int(re.sub("[^0-9]", "", value)) // 1000000
    elif re.match(r"[0-9]{1,15}u", str(value)):
      cpu = int(re.sub("[^0-9]", "", value)) // 1000

    return int(cpu)

  def memory_as_mb(value):
    if re.match(r"[0-9]{1,9}Mi?", str(value)):
      mem = re.sub("[^0-9]", "", value)
    elif re.match(r"[0-9]{1,9}Ki?", str(value)):
      mem = re.sub("[^0-9]", "", value)
      mem = int(mem) // 1024
    elif re.match(r"[0-9]{1,9}Gi?", str(value)):
      mem = re.sub("[^0-9]", "", value)
      mem = int(mem) * 1024
    else:
      mem = re.sub("[^0-9]", "", value)
      mem = int(mem) // 1024 // 1024

    return int(mem)


class KubeConfig:
    def __init__(self, context = None, kube_config_file = None):
        self.__context = context
        if context != None and not self.__is_context_exists(context):
            raise ValueError(f'Oops! Cannot find "{context}" context in kube-config file')

        params = {'context': context, 'config_file': kube_config_file}
        config.load_kube_config(**params)

    def __list_contexts(self):
        contexts, active_context = config.list_kube_config_contexts()
        if not contexts:
            raise ValueError('Oops! Cannot find any context in kube-config file')

        return contexts, active_context

    def __is_context_exists(self, context_name):
        contexts, _ = self.__list_contexts()
        contexts = [context['name'] for context in contexts]

        return context_name in contexts

    def __get_current_context(self):
        try:
            contexts, active_context = self.__list_contexts()

            return active_context['context']
        except KeyError:
            return 'default'

    def get_config_cluster(self):
        return self.__get_current_context()['cluster']

    def get_config_namespace(self):
        return self.__get_current_context()['namespace']

    def get_cluster(self):
        return self.__context if self.__context else self.get_config_cluster()


class KubeNodeResourceScrapper:
    def __init__(self, cluster):
        api_client = config.new_client_from_config(context=cluster)
        self._core_api_client = client.CoreV1Api(api_client=api_client)
        self._custom_objects_api_client = client.CustomObjectsApi(api_client=api_client)

    # nodes utilisation + sum of pod's requests and limits
    def get_node_resources(self, label_selector = None):
        params = {"label_selector": label_selector} if not label_selector == None else {}
        nodes = self._custom_objects_api_client.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes", **params)

        r = {}
        # TODO run in parallel
        for node in nodes["items"]:
            node_name = node["metadata"]["name"]

            requests, limits = self.get_pod_resources(node_name)

            r[node_name] = {
                "requests": requests,
                "limits": limits,
                "utilisation": {
                   "cpu": Converter.cpu_as_milicores(node["usage"]["cpu"]),
                   "memory": Converter.memory_as_mb(node["usage"]["memory"]),
                   "window": node["window"],
                   "timestamp": node["timestamp"],
                   "application": node["metadata"]["labels"]["application"],
               }
            }

        return r

    # nodes info, labels, capacity
    def get_nodes(self, label_selector = None):
        params = {"label_selector": label_selector} if not label_selector == None else {}
        nodes_list = self._core_api_client.list_node(**params)

        nodes = {}
        for node in nodes_list.items:
            for i in node.status.addresses:
                if i.type == "InternalIP":
                    internal_ip = i.address
                elif i.type == "Hostname":
                    hostname = i.address

            nodes[node.metadata.name] = {
                "addresses": {
                    "internal_ip": internal_ip,
                    "hostname": hostname,
                },
                "allocatable": {
                    "cpu": Converter.cpu_as_milicores(node.status.allocatable["cpu"]),
                    "memory": Converter.memory_as_mb(node.status.allocatable["memory"]),
                    "ephemeral-storage": Converter.memory_as_mb(node.status.allocatable["ephemeral-storage"]),
                },
                "capacity": {
                    "cpu": Converter.cpu_as_milicores(node.status.capacity["cpu"]),
                    "memory": Converter.memory_as_mb(node.status.capacity["memory"]),
                    "ephemeral-storage": Converter.memory_as_mb(node.status.capacity["ephemeral-storage"]),
                },
                "labels": {
                    "application": node.metadata.labels["application"],
                    "environment": node.metadata.labels["environment"],
                    "kubernetes.io/hostname": node.metadata.labels["kubernetes.io/hostname"],
                    "node.kubernetes.io/instance-type": node.metadata.labels["node.kubernetes.io/instance-type"],
                    "topology.kubernetes.io/zone": node.metadata.labels["topology.kubernetes.io/zone"],
                }
            }

        return nodes

    # sum pod's requests and limits by node
    def get_pod_resources(self, node_name):
        pods = self._core_api_client.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name},status.phase=Running")

        req_cpu = 0
        req_memory = 0
        lim_cpu = 0
        lim_memory = 0
        for pod in pods.items:
            for c in pod.spec.containers:
                if c.resources.requests:
                    if "cpu" in c.resources.requests:
                        req_cpu += Converter.cpu_as_milicores(c.resources.requests["cpu"])
                    if "memory" in c.resources.requests:
                        req_memory += Converter.memory_as_mb(c.resources.requests["memory"])
                if c.resources.limits:
                    if "cpu" in c.resources.limits:
                        lim_cpu += Converter.cpu_as_milicores(c.resources.limits["cpu"])
                    if "memory" in c.resources.limits:
                        lim_memory += Converter.memory_as_mb(c.resources.limits["memory"])

        return {"cpu": req_cpu, "memory": req_memory}, {"cpu": lim_cpu, "memory": lim_memory}


class Calculator:
    class Stat:
        def __init__(self):
            self.alloc = self.req = self.lim = self.util = 0

        def calc(self):
            self.req_per_alloc = self.req / self.alloc * 100
            self.lim_per_alloc = self.lim / self.alloc * 100
            self.util_per_alloc = self.util / self.alloc * 100

            self.util_per_req = self.util / self.req * 100
            self.util_per_lim = self.util / self.lim * 100

            return self

    # TODO redo nodes to ValueObject
    def build_table(nodes, resources):
        table = []
        cpu_stat = Calculator.Stat()
        memory_stat = Calculator.Stat()

        for node_name, node in resources.items():
            cpu_stat.util += node["utilisation"]["cpu"] if "cpu" in node["utilisation"] else 0
            cpu_stat.req += node["requests"]["cpu"] if "cpu" in node["requests"] else 0
            cpu_stat.lim += node["limits"]["cpu"] if "cpu" in node["limits"] else 0
            memory_stat.util += node["utilisation"]["memory"] if "memory" in node["utilisation"] else 0
            memory_stat.req += node["requests"]["memory"] if "memory" in node["requests"] else 0
            memory_stat.lim += node["limits"]["memory"] if "memory" in node["limits"] else 0

            cpu_alloc = nodes[node_name]["allocatable"]["cpu"] if "cpu" in nodes[node_name]["allocatable"] else 0
            cpu_stat.alloc += cpu_alloc
            memory_alloc = nodes[node_name]["allocatable"]["memory"] if "memory" in nodes[node_name]["allocatable"] else 0
            memory_stat.alloc += memory_alloc

            row = [
                node_name,
                f'{cpu_alloc}m',
                f'{node["utilisation"]["cpu"]}m /{node["utilisation"]["cpu"]/cpu_alloc*100:6.1f}%',
                f'{node["requests"]["cpu"]}m /{node["requests"]["cpu"]/cpu_alloc*100:6.1f}%',
                f'{node["limits"]["cpu"]}m /{node["limits"]["cpu"]/cpu_alloc*100:6.1f}%',
                f'{node["utilisation"]["cpu"]/node["requests"]["cpu"]*100:6.1f}%',
                f'{node["utilisation"]["cpu"]/node["limits"]["cpu"]*100:6.1f}%',
                f'{memory_alloc}Mi',
                f'{node["utilisation"]["memory"]}Mi /{node["utilisation"]["memory"]/memory_alloc*100:6.1f}%',
                f'{node["requests"]["memory"]}Mi /{node["requests"]["memory"]/memory_alloc*100:6.1f}%',
                f'{node["limits"]["memory"]}Mi /{node["limits"]["memory"]/memory_alloc*100:6.1f}%',
                f'{node["utilisation"]["memory"]/node["requests"]["memory"]*100:6.1f}%',
                f'{node["utilisation"]["memory"]/node["limits"]["memory"]*100:6.1f}%',
            ]

            table.append(row)

        return table, cpu_stat.calc(), memory_stat.calc()


class Printer:
    def __init__(self, verbosity_enabled=False):
        self.__verbosity_enabled = verbosity_enabled

    def print(self, string):
        if self.__verbosity_enabled:
            print(string)

    def print_table(self, table, cpu_stat, memory_stat):
        # pre-define header
        header = self.__get_table_header()
        table.insert(0, header)

        # append footer to the table
        footer = self.__get_table_footer(cpu_stat, memory_stat)
        table.append(footer)

        # define col width (based on max col width)
        col_width = self.__calc_col_width(table)

        # print table
        print('')
        self.__print_table(table, col_width, True, True)

    def print_summary(self, cpu_stat, memory_stat, prefix=''):
        if self.__verbosity_enabled:
            print('')
            self.__print_summary_multiline(cpu_stat, memory_stat, prefix)
        else:
            self.__print_summary_oneline(cpu_stat, memory_stat, prefix)

    def __print_table(self, table, col_width, is_header=False, is_footer=False):
        row_count = len(table)
        for row_index, row in enumerate(table):
            col_align = "^" if row_index == 0 else ">"

            for col_index, col in enumerate(row):
                align = col_align if col_index != 0 else "<"
                row[col_index] = f"{row[col_index]: {align}{col_width[col_index]}}"
            row = ' | '.join(row)
            print(row)

            if is_header and row_index == 0 or is_footer and row_index == row_count-2:
                print(f'{"-" * len(row)}')

    def __calc_col_width(self, table):
        col_width = {}
        for row in table:
            for i, col in enumerate(row):
                l = len(col)
                if not i in col_width or l > col_width[i]:
                    col_width[i] = l
        return col_width

    def __get_table_header(self):
        return [
           "Node",
           "CPU A",
           "CPU U (% U/A)",
           "CPU R (% R/A)",
           "CPU L (% L/A)",
           "%C U/R",
           "%C U/L",
           "RAM A",
           "RAM U (% U/A)",
           "RAM R (% R/A)",
           "RAM L (% L/A)",
           "%R U/R",
           "%R U/L",
       ]

    def __get_table_footer(self, cpu_stat, memory_stat):
        return [
           "Total",
           f'{cpu_stat.alloc}m',
           f'{cpu_stat.util}m /{cpu_stat.util_per_alloc:6.1f}%',
           f'{cpu_stat.req}m /{cpu_stat.req_per_alloc:6.1f}%',
           f'{cpu_stat.lim}m /{cpu_stat.lim_per_alloc:6.1f}%',
           f'{cpu_stat.util_per_req:6.1f}%',
           f'{cpu_stat.util_per_lim:6.1f}%',
           f'{memory_stat.alloc}Mi',
           f'{memory_stat.util}Mi /{memory_stat.util_per_alloc:6.1f}%',
           f'{memory_stat.req}Mi /{memory_stat.req_per_alloc:6.1f}%',
           f'{memory_stat.lim}Mi /{memory_stat.lim_per_alloc:6.1f}%',
           f'{memory_stat.util_per_req:6.1f}%',
           f'{memory_stat.util_per_lim:6.1f}%',
       ]

    def __print_summary_multiline(self, cpu_stat, memory_stat, prefix):
        print(f"Summary: {'(' + prefix + ')' if prefix else ''}")
        table = [
            [
                "Cluster's CPU|RAM average UTILISATION",
                f'{"CPU: "}{cpu_stat.util_per_alloc:6.1f}%',
                f'{"RAM: "}{memory_stat.util_per_alloc:6.1f}%',
            ],
            [
                "Cluster's CPU|RAM average REQUESTS",
                f'{"CPU: "}{cpu_stat.req_per_alloc:6.1f}%',
                f'{"RAM: "}{memory_stat.req_per_alloc:6.1f}%',
            ],
            [
                "Cluster's CPU|RAM REQUESTS performance",
                f'{"CPU: "}{(cpu_stat.req_per_alloc - cpu_stat.util_per_alloc) / cpu_stat.util_per_alloc * 100:6.1f}%',
                f'{"RAM: "}{(memory_stat.req_per_alloc - memory_stat.util_per_alloc) / memory_stat.util_per_alloc * 100:6.1f}%',
            ],
            ["hint: (Av.%Req - Av.%Util) / Av.%Util * 100%"]
        ]
        self.__print_table(table, self.__calc_col_width(table))

    def __print_summary_oneline(self, cpu_stat, memory_stat, prefix):
        table = [[
            f"Cluster {prefix}",
            f'{"CPU_U_R:"}{cpu_stat.util_per_alloc:6.1f}% / {cpu_stat.req_per_alloc:6.1f}%',
            f'{"CPU_RU/U:"}{(cpu_stat.req_per_alloc - cpu_stat.util_per_alloc) / cpu_stat.util_per_alloc * 100:6.1f}%',
            f'{"RAM_U_R:"}{memory_stat.util_per_alloc:6.1f}% / {memory_stat.req_per_alloc:6.1f}%',
            f'{"RAM_RU/U:"}{(memory_stat.req_per_alloc - memory_stat.util_per_alloc) / memory_stat.util_per_alloc * 100:6.1f}%',
        ]]
        self.__print_table(table, self.__calc_col_width(table))

#------------------------------#

def get_args():
    parser=argparse.ArgumentParser()

    parser.add_argument('--kube-config-context', '-c', help="a context name to work with. Optional, the one from the kube config will be used by default", type=str)
    parser.add_argument('--kube-config-file', '-f', help="a config file to fetch cluster info from. Optional", type=str)
    parser.add_argument('--label-selector', '-s', help="a label selector to filter nodes to fetch data for. Optional, empty by default", type=str, default='')
    parser.add_argument('--print-nodes', help="if specified, a table with node details gets printed as output. Optional flag, disabled by default", action='store_true')
    parser.add_argument('--verbose', '-v', help="enables verbose output mode. Optional flag, disabled by default", action='store_true')

    return parser.parse_args()

def main():
    # get script args
    args = get_args()
    label_selector = args.label_selector

    # kube config
    clusterConfig = KubeConfig(context=args.kube_config_context, kube_config_file=args.kube_config_file)
    cluster = clusterConfig.get_cluster()

    printer = Printer(verbosity_enabled=args.print_verbosity)
    printer.print(f"KUBE_CLUSTER: {cluster} // active context - {cluster}{f' (overwritten by script argument - {clusterConfig.get_cluster()})' if clusterConfig.get_config_cluster() != cluster else ''} ")
    printer.print(f"LABEL_SELECTOR: {label_selector}")

    # fetch data
    scrapper = KubeNodeResourceScrapper(cluster=cluster)
    nodes = scrapper.get_nodes(label_selector)
    resources = scrapper.get_node_resources(label_selector)

    # build table and calc stat
    table, cpu_stat, memory_stat = Calculator.build_table(nodes, resources)

    # print table
    if args.print_nodes:
        printer.print_table(table, cpu_stat, memory_stat)

    # print summary
    printer.print_summary(cpu_stat, memory_stat, f"{cluster} / {label_selector}")

#------------------------------#

if __name__ == '__main__':
    main()
