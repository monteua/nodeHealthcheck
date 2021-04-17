from abc import ABC
from sshControl import NodeRestart

import requests
import time
from decouple import config


nodes = dict()
timeout = 60  # seconds
last_updated = time.time()  # when the last API request was sent


class API(ABC):

    def __init__(self):
        self.endpoint = "https://nodes.presearch.org/api/nodes/status/" + config('API_KEY')

    def get_update_from_api(self):
        global nodes, timeout, last_updated
        
        if len(nodes) == 0 or time.time() - last_updated > timeout:
            print("Sending the api request")
            nodes = requests.get(self.endpoint).json()['nodes']
            last_updated = time.time()

    def get_forced_update_from_api(self):
        global nodes, last_updated

        print("Sending the forced api request")
        nodes = requests.get(self.endpoint).json()['nodes']
        last_updated = time.time()

    def get_node_list(self):
        global nodes

        self.get_update_from_api()
        return [nodes[node]['meta']['description'] for node in nodes]

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
        global nodes

        msg = """Name: {description}\nURL: {url}\nServer Description: {server_description} \
        \nServer Url: {server_url}\nGateway Pool: {gateway_pool}\nRemote Address: {remote_addr}\nVersion: {version} \
        \nConnected: {status_connected} ({status_minutes_in_current_state})\nBlocked: {status_blocked} \
        \nIn current state since: {status_in_current_state_since}"""

        self.get_update_from_api()
        for node in nodes:
            if nodes[node]['meta']['description'] == node_description:
                description = nodes[node]['meta']['description']
                url = nodes[node]['meta']['url']
                server_description = nodes[node]['meta']['server_description']
                server_url = nodes[node]['meta']['server_url']
                gateway_pool = nodes[node]['meta']['gateway_pool']
                remote_addr = nodes[node]['meta']['remote_addr']
                version = nodes[node]['meta']['version']
                status_connected = nodes[node]['status']['connected']
                status_blocked = nodes[node]['status']['blocked']
                status_in_current_state_since = nodes[node]['status']['in_current_state_since']
                status_minutes_in_current_state = nodes[node]['status']['minutes_in_current_state']

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
                    status_in_current_state_since=status_in_current_state_since
                )

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

    def get_node_ip(self, node_name):
        global nodes

        self.get_update_from_api()
        for node in nodes:
            if nodes[node]['meta']['description'] == node_name:
                print(nodes[node]['meta']['remote_addr'])
                return nodes[node]['meta']['remote_addr']
