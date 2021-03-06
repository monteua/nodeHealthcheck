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

    def get_earnings_per_day_for_last_30_days(self):
        conn = sqlite3.connect(os.path.dirname(__file__) + '/data.db')
        curs = conn.cursor()

        stats = curs.execute(''' SELECT date, SUM(earned_tokens) 
                                    FROM stats 
                                    GROUP BY date 
                                    ORDER BY date 
                                    DESC 
                                    LIMIT 31; 
                             ''').fetchall()
        conn.close()
        return sorted(stats)

    def generate_graph_per_node(self):
        stats = self.get_stats_for_last_30_days()

        # x axis values
        x = [datetime.strptime(i, "%Y-%m-%d").strftime("%b %d") for i in list(reversed(list(stats.keys())))]
        x.sort(key=lambda date: datetime.strptime(date, '%b %d'))

        # nodes
        nodes = list(stats.get(list(stats.keys())[-1]))
        min_value, max_value = 0, 0

        for node in nodes:
            dates_for_stats = [
                datetime.strptime(i, "%Y-%m-%d").strftime("%Y-%m-%d") for i in list(reversed(list(stats.keys())))
            ]
            dates_for_stats.sort(key=lambda date: datetime.strptime(date, '%Y-%m-%d'))
            # plotting the points for each node
            # y axis values
            y = [float(stats.get(date).get(node)) if stats.get(date).get(node) is not None else 0.0 for date in dates_for_stats]
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
        plt.gcf().set_dpi(200)
        plt.legend()

        step = 0.1 if max_value < 10 else 0.5
        plt.yticks(np.arange(min_value, max_value, step))
        plt.grid(True)
        # plt.show()

        if not os.path.exists(os.path.dirname(__file__) + "/img"):
            os.makedirs(os.path.dirname(__file__) + "/img")

        plt.savefig(os.path.dirname(__file__) + '/img/graph.png')
        plt.close()

    def generate_graph_per_day_for_all_nodes(self):
        stats = self.get_earnings_per_day_for_last_30_days()

        # x axis values
        x = [datetime.strptime(i[0], "%Y-%m-%d").strftime("%b %d") for i in list(list(stats))]

        # y axis values
        y = [float(day[1]) for day in stats]

        plt.plot(x, y)

        # naming the x axis
        plt.xlabel('Date')
        # naming the y axis
        plt.ylabel('Tokens')

        # giving a title to my graph
        plt.title('Earnings Graph Per Day For All Nodes(past 30 days)')

        # function to show the plot
        plt.gcf().set_size_inches(25, 10.5, forward=True)
        plt.gcf().set_dpi(200)

        step = 0.5 if round(max(y)) < 20 else 1
        plt.yticks(np.arange(round(min(y)), round(max(y)), step))

        for i, v in enumerate(y):
            plt.text(i + 0.3, v + 0.3, "%.2f" % v, ha="center")

        plt.grid(True)
        # plt.show()

        if not os.path.exists(os.path.dirname(__file__) + "/img"):
            os.makedirs(os.path.dirname(__file__) + "/img")

        plt.savefig(os.path.dirname(__file__) + '/img/graph.png')
        plt.close()