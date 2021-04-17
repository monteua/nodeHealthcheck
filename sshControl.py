import traceback
import os
import sqlite3
import paramiko

from decouple import config


class NodeRestart:

    @staticmethod
    def restart(node_ip):
        conn = sqlite3.connect(os.getcwd() + '/data.db')
        curs = conn.cursor()

        node_auth_type = curs.execute("SELECT auth_type FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()
        node_password = curs.execute("SELECT password FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()
        node_user = curs.execute("SELECT user FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()

        if node_user is not None:
            try:
                connection_password = node_password[0] if node_auth_type[0] == "password" \
                    else paramiko.RSAKey.from_private_key_file(node_password[0])

                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                print("connecting")
                if node_auth_type[0] == "password":
                    c.connect(hostname=node_ip, username=node_user[0], password=connection_password)
                else:
                    c.connect(hostname=node_ip, username=node_user[0], pkey=connection_password)

                print("connected")
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
                print("Executing {}".format(command))
                stdin, stdout, stderr = c.exec_command(command)
                print(stdout.read())
                print("Errors")
                print(stderr.read())
                c.close()
            except TypeError:
                return traceback.print_exc()
        else:
            conn.close()
            return "Node is not supported: " + node_ip

        conn.close()
        return "\U0001F3D7 Executing the restart command" + "\n\U00002705 Node was successfully restarted"
