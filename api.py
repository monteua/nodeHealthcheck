import logging
import requests
import time
from decouple import config

from abc import ABC
from sshControl import NodeRestart

nodes = dict()
nodes_stats = dict()
timeout = 60  # seconds
last_updated = time.time()  # when the last API request was sent
last_updated_stats = time.time()

logging.basicConfig(filename="log",
                    filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


class API(ABC):

    def __init__(self):
        self.endpoint = "https://nodes.presearch.org/api/nodes/status/" + config('API_KEY')

    def get_update_from_api(self):
        global nodes, timeout, last_updated

        if len(nodes) == 0 or time.time() - last_updated > timeout:
            logging.info("Sending the api request")
            nodes = requests.get(self.endpoint).json()['nodes']
            last_updated = time.time()

    def get_forced_update_from_api(self):
        global nodes, last_updated

        logging.info("Sending the forced api request")
        nodes = requests.get(self.endpoint).json()['nodes']
        last_updated = time.time()

    def get_stats_for_nodes(self, is_forced):
        global nodes_stats, timeout, last_updated_stats

        if len(nodes_stats) == 0 or time.time() - last_updated_stats > timeout and not is_forced:
            logging.info("Sending the api request with stats parameter")
            nodes_stats = requests.get(self.endpoint + "?stats=true").json()['nodes']
            last_updated_stats = time.time()
        elif is_forced:
            logging.info("Sending the forced api request with stats parameter")
            nodes_stats = requests.get(self.endpoint + "?stats=true").json()['nodes']
            last_updated_stats = time.time()

    def get_node_list(self):
        global nodes

        self.get_update_from_api()
        return [nodes[node]['meta']['description'] for node in nodes]

    def get_node_ips(self):
        global nodes

        self.get_update_from_api()
        return [nodes[node]['meta']['remote_addr'] for node in nodes]

    def get_status_for_nodes(self):
        global nodes

        response = list()
        msg = """{status} {description} | {gateway_pool} | v{version}"""

        self.get_update_from_api()
        for node in nodes:
            description = nodes[node]['meta']['description']
            gateway_pool = nodes[node]['meta']['gateway_pool']
            version = nodes[node]['meta']['version']
            status_connected = nodes[node]['status']['connected']

            response.append(msg.format(
                description=description,
                status="\U0001F7E2" if status_connected else "\U0001F534",
                version=version,
                gateway_pool=gateway_pool
            ))

        return "\n".join(response)

    def get_status_for_node(self, node_description):
        global nodes_stats

        msg = """+------------------------------------+ \
        \nName: {description}\nURL: {url}\nServer Description: {server_description} \
        \nServer Url: {server_url}\nGateway Pool: {gateway_pool}\nRemote Address: {remote_addr}\nVersion: {version} \
        \nConnected: {status_connected} ({status_minutes_in_current_state})\nBlocked: {status_blocked} \
        \nIn current state since: {status_in_current_state_since} \
        \n-------------------------------------- \
        \nStats [24h] \
        \nNumber of Connections: {number_of_connections}\nNumber of Disconnections: {number_of_disconnections} \
        \nReliability Score: {reliability_score}\nRequests Received: {requests_received} \
        \nPRE earned: {pre_earned} \
        \n+------------------------------------+"""

        self.get_stats_for_nodes(False)
        for node in nodes_stats:
            if nodes_stats[node]['meta']['description'] == node_description:
                description = nodes_stats[node]['meta']['description']
                url = nodes_stats[node]['meta']['url']
                server_description = nodes_stats[node]['meta']['server_description']
                server_url = nodes_stats[node]['meta']['server_url']
                gateway_pool = nodes_stats[node]['meta']['gateway_pool']
                remote_addr = nodes_stats[node]['meta']['remote_addr']
                version = nodes_stats[node]['meta']['version']
                status_connected = nodes_stats[node]['status']['connected']
                status_blocked = nodes_stats[node]['status']['blocked']
                status_in_current_state_since = nodes_stats[node]['status']['in_current_state_since']
                status_minutes_in_current_state = nodes_stats[node]['status']['minutes_in_current_state']

                # stats
                number_of_connections = nodes_stats[node]['period']['connections']['num_connections']
                number_of_disconnections = nodes_stats[node]['period']['disconnections']['num_disconnections']
                reliability_score = nodes_stats[node]['period']['avg_reliability_score']
                requests_received = nodes_stats[node]['period']['total_requests']
                pre_earned = nodes_stats[node]['period']['total_pre_earned']

                day = int(int(status_minutes_in_current_state) / 1440)
                hour = int(int(status_minutes_in_current_state) % 1440 / 60)
                minutes = (int(status_minutes_in_current_state) - day * 1440 - hour * 60)

                return msg.format(
                    description=description,
                    url=url,
                    server_description=server_description,
                    server_url=server_url,
                    gateway_pool=gateway_pool,
                    remote_addr=remote_addr,
                    version=version,
                    status_connected="\U0001F7E2" if status_connected else "\U0001F534",
                    status_minutes_in_current_state=str(day) + "d " + str(hour) + "h " + str(minutes) + "m",
                    status_blocked="Yes" if status_blocked else "No",
                    status_in_current_state_since=status_in_current_state_since,
                    number_of_connections=number_of_connections,
                    number_of_disconnections=number_of_disconnections,
                    reliability_score=str(round(reliability_score, 2)) + " \u26a0\ufe0f" if int(
                        reliability_score) < 70 else str(round(reliability_score, 2)) + " \U0001f7e2",
                    requests_received=requests_received,
                    pre_earned=round(pre_earned, 2)
                )

    def get_nodes_stats_report(self):
        global nodes_stats

        msg = """\n+------------------------------------+ \
                \nName: {description} \
                \nGateway Pool: {gateway_pool}\nRemote Address: {remote_addr} \
                \nVersion: {version} \
                \n \
                \nStats [24h] \
                \nNumber of Connections: {number_of_connections}\nNumber of Disconnections: {number_of_disconnections} \
                \nReliability Score: {reliability_score}\nRequests Received: {requests_received} \
                \nPRE earned: {pre_earned}"""
        result_msg = ""

        self.get_stats_for_nodes(False)
        for node in nodes_stats:
            description = nodes_stats[node]['meta']['description']
            gateway_pool = nodes_stats[node]['meta']['gateway_pool']
            remote_addr = nodes_stats[node]['meta']['remote_addr']
            version = nodes_stats[node]['meta']['version']

            # stats
            number_of_connections = nodes_stats[node]['period']['connections']['num_connections']
            number_of_disconnections = nodes_stats[node]['period']['disconnections']['num_disconnections']
            reliability_score = nodes_stats[node]['period']['avg_reliability_score']
            requests_received = nodes_stats[node]['period']['total_requests']
            pre_earned = nodes_stats[node]['period']['total_pre_earned']

            result_msg += msg.format(
                description=description,
                gateway_pool=gateway_pool,
                remote_addr=remote_addr,
                version=version,
                number_of_connections=number_of_connections,
                number_of_disconnections=number_of_disconnections,
                reliability_score=str(round(reliability_score, 2)) + " \u26a0\ufe0f" if int(
                    reliability_score) < 70 else str(round(reliability_score, 2)) + " \U0001f7e2",
                requests_received=requests_received,
                pre_earned=round(pre_earned, 2)
            )
        return result_msg

    def get_node_ip(self, node_name):
        global nodes

        self.get_update_from_api()
        for node in nodes:
            if nodes[node]['meta']['description'] == node_name:
                logging.info(nodes[node]['meta']['remote_addr'])
                return nodes[node]['meta']['remote_addr']

    def get_node_name(self, node_ip):
        global nodes

        self.get_update_from_api()
        for node in nodes:
            if nodes[node]['meta']['remote_addr'] == node_ip:
                logging.info(nodes[node]['meta']['description'])
                return nodes[node]['meta']['description']

    def health_check(self):
        global nodes

        response = list()
        msg = """{status} {description}"""

        self.get_update_from_api()
        for node in nodes:
            description = nodes[node]['meta']['description']
            status_connected = nodes[node]['status']['connected']
            ip = nodes[node]['meta']['remote_addr']

            if not status_connected:
                response.append(msg.format(description=description, status="\U0001F534"))
                response.append(NodeRestart().restart(ip))
        return response

    def restart_all_nodes(self):
        global nodes

        response = list()
        msg = """{status} {description}"""

        for ip in self.get_node_ips():
            description = self.get_node_name(ip)

            response.append(msg.format(description=description, status="\U0001F534"))
            response.append(NodeRestart().restart(ip))

        return response
