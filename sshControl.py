import sqlite3
import paramiko


class NodeRestart:

    @staticmethod
    def restart(node_ip):
        conn = sqlite3.connect('data.db')
        curs = conn.cursor()

        node_auth_type = curs.execute("SELECT auth_type FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()[0]
        node_password = curs.execute("SELECT password FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()[0]
        node_user = curs.execute("SELECT user FROM nodes WHERE node_ip = ?", (node_ip,)).fetchone()[0]

        connection_password = node_password if node_auth_type == "password" else paramiko.RSAKey.from_private_key_file(node_password)

        if node_user is not None:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print("connecting")
            if node_auth_type == "password":
                c.connect(hostname=node_ip, username=node_user, password=connection_password)
            else:
                c.connect(hostname=node_ip, username=node_user, pkey=connection_password)

            print("connected")
            command = "sudo systemctl restart presearch"
            print("Executing {}".format(command))
            stdin, stdout, stderr = c.exec_command(command)
            print(stdout.read())
            print("Errors")
            print(stderr.read())
            c.close()
        else:
            conn.close()
            return "Node is not supported: " + node_ip

        conn.close()
        return "Executing {}".format(command)
