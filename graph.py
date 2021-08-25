import os

from datetime import datetime, timedelta
import sqlite3

import matplotlib.pyplot as plt
import numpy as np


class Graph:

    def __init__(self):
        self.stats = dict()

    def get_stats_for_last_30_days(self):
        conn = sqlite3.connect(os.path.dirname(__file__) + '/data.db')
        curs = conn.cursor()

        today_date = datetime.today()
        min_date = (today_date - timedelta(days=31)).strftime("%Y-%m-%d")

        for node_public_key in curs.execute(''' SELECT DISTINCT node_public_key FROM stats ''').fetchall():
            node_data = curs.execute(''' SELECT node_description, date, earned_tokens 
                                        FROM stats 
                                        WHERE date >=? 
                                        AND node_public_key =? ''', (min_date, node_public_key[0])).fetchall()

            for i in node_data:
                node_description = i[0]
                date = i[1]
                tokens = i[2]
                if date in self.stats.keys():
                    self.stats[date].update({node_description: tokens})
                else:
                    self.stats[date] = {node_description: tokens}

        conn.close()
        return self.stats

    def generate_graph(self):
        stats = self.get_stats_for_last_30_days()

        # x axis values
        x = [datetime.strptime(i, "%Y-%m-%d").strftime("%b %-d") for i in list(reversed(list(stats.keys())))]

        # nodes
        nodes = list(stats.get(list(stats.keys())[0]))
        min_value, max_value = 0, 0

        for node in nodes:
            # plotting the points for each node
            # y axis values
            y = [float(stats.get(date).get(node)) if stats.get(date).get(node) is not None else 0.0 for date in
                 list(reversed(list(stats.keys())))]
            min_value = min(y) if min(y) < min_value else min_value
            max_value = max(y) if max(y) > max_value else max_value
            plt.plot(x, y, label=node)


        # naming the x axis
        plt.xlabel('Date')
        # naming the y axis
        plt.ylabel('Tokens')

        # giving a title to my graph
        plt.title('Earnings Graph (past 30 days)')

        # function to show the plot
        plt.gcf().set_size_inches(25, 10.5, forward=True)
        plt.gcf().set_dpi(100)
        plt.legend()

        plt.yticks(np.arange(min_value, max_value, 0.5))
        #plt.show()
        plt.savefig(os.path.dirname(__file__) + '/img/graph.png')
