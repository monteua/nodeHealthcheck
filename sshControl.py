import logging
import traceback
import os
import sqlite3
import paramiko

from decouple import config

if not os.path.exists(os.path.dirname(__file__) + "/logs"):
    os.makedirs(os.path.dirname(__file__) + "/logs")

logging.basicConfig(filename=os.path.dirname(__file__) + "/logs/log",
                    filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


class NodeRestart:

    def __init__(self):
        self.conn = sqlite3.connect(os.path.dirname(__file__) + '/data.db')
        self.curs = self.conn.cursor()
        self.table_exists()

    def table_exists(self):
        data = self.curs.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='nodes' ''')
        if data.fetchone()[0] != 1:
            logging.info("Creating a new table: nodes")
            self.curs.execute(''' create table nodes
                                (
                                    node_id   INTEGER      not null
                                        primary key autoincrement,
                                    node_ip   VARCHAR(128),
                                    auth_type VARCHAR(128),
                                    password  VARCHAR(128),
                                    user      VARCHAR(128) not null
                                );
                            ''')
            self.conn.commit()

    def restart(self, node_ip):
        node_auth_type = self.curs.execute("SELECT auth_type FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()
        node_password = self.curs.execute("SELECT password FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()
        node_user = self.curs.execute("SELECT user FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()

        if node_user is not None:
            try:
                connection_password = node_password[0] if node_auth_type[0] == "password" \
                    else paramiko.RSAKey.from_private_key_file(node_password[0])

                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                logging.info("connecting")
                if node_auth_type[0] == "password":
                    c.connect(hostname=node_ip, username=node_user[0], password=connection_password)
                else:
                    c.connect(hostname=node_ip, username=node_user[0], pkey=connection_password)

                logging.info("connected")
                # command = "sudo systemctl restart presearch" // if you're running node as a service
                command = "docker stop presearch-node ; " \
                          "docker rm presearch-node ; " \
                          "docker stop presearch-auto-updater ; " \
                          "docker rm presearch-auto-updater ; " \
                          "docker run -d --name presearch-auto-updater " \
                          "--restart=unless-stopped -v /var/run/docker.sock:/var/run/docker.sock " \
                          "containrrr/watchtower --cleanup --interval 300 presearch-node ; " \
                          "docker pull presearch/node ; " \
                          "docker run -dt --name presearch-node --restart=unless-stopped " \
                          "-v presearch-node-storage:/app/node " \
                          "-e REGISTRATION_CODE=" + config('REGISTRATION_CODE') + " presearch/node"
                logging.info("Executing {}".format(command))
                stdin, stdout, stderr = c.exec_command(command)
                logging.info(stdout.read())
                logging.info("Errors")
                logging.info(stderr.read())
                c.close()
            except TypeError:
                return traceback.print_exc()
            except Exception:
                return "Unable to connect: " + node_ip
        else:
            self.conn.close()
            return "Node is not supported: " + node_ip

        self.conn.close()
        return "\U0001F3D7 Executing the restart command" + "\n\U00002705 Node was successfully restarted"