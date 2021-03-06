# Presearch Node Telegram Bot

### Available functionality:
1. Getting the aggregated report about the node current status
2. Getting details for each node
3. Manual restart for the particular node
4. Watchdog command, which will restart the node after it goes offline

### Available commands:
```
/nodes - used to show the aggregated details for each node (status, description, version, etc.) \
/manage - used to show the details for particular node and restarts it (if needed) \
/watchdog - launches the monitoring script (it will check the status for each node and restarts it if it goes offline) \
/force_update - bypasses the limit of 1 minute for each api call and gets a fresh node statuses
```

## Setup Instruction

1. Get the API token from the [@BotFather](https://t.me/BotFather)
2. Get the Node API key from the Node Stats page: https://nodes.presearch.com/node/xxxxx/stats
3. Get the registration code from the [Node Dashboard](https://nodes.presearch.com/dashboard)

4. Clone the repository repository and rename the .env.example, data.db.example files removing the .example extension
5. Put your APIs keys, registration code and your telegram username into the .env file
6. Insert into the data.db the IP and authentication data, so the script could connect to your node
6.1. Connect to the DB with a command: 
```
sqlite3 data.db
```
Then add your nodes with a following SQL query:
```
INSERT INTO nodes(node_ip, auth_type, password, user) VALUES ("YOUR_NODE_IP", "AUTH_TYPE", "AUTH_DATA", "USER")    
``` 
    * Replace the YOUR_NODE_IP with the IP address of your node
    * Replace the AUTH_TYPE with the type of authentication used on your server: "private_key" or "password" 
    * Replace the AUTH_DATA with the password or with the location of your private key
    * Replace the USER with the username used to connect to your server

7. Run the command to install required packages
```
sudo -H pip install -r requirements.txt
```
8. Run the script

8.1. Run as a service

8.1.1. Create a service
```
sudo nano /etc/systemd/system/nodeBot.service
```
and put following into the file replacing the path to the repository
```
[Unit]
After=network.service

[Service]
ExecStart=/usr/bin/python3 /PATH_TO_CLONED_REPOSITORY/bot.py

[Install]
WantedBy=default.target
```
Save changes.

8.1.2. Reload the daemon and start the service:
```
sudo chmod 664 /etc/systemd/system/nodeBot.service
sudo systemctl daemon-reload
sudo systemctl enable nodeBot.service
sudo systemctl start nodeBot
sudo systemctl status nodeBot
```

8.2. Run as a docker container

From the project directory run:
```
docker compose up -d
```

To stop the bot, run:
```
docker compose down
```

## Examples

List of running nodes:
![Node List](./examples/nodes_list.png)

Manual node restart:
![Manual Restart](./examples/manual_restart.png)

Automatic restart after node disconnects:
![Automatic Restart](./examples/automatic_restart.png)