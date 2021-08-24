from datetime import datetime, timedelta

import os

import sqlite3

import matplotlib.pyplot as plt


class Graph:

    def __init__(self):
        self.stats = dict()

    def get_stats_for_last_30_days(self):
        conn = sqlite3.connect('data.db')
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
        # x axis values
        x = [1, 2, 3]
        # corresponding y axis values
        y = [2, 4, 1]

        # plotting the points
        plt.plot(x, y, label="Node1")

        # naming the x axis
        plt.xlabel('Date')
        # naming the y axis
        plt.ylabel('Tokens')

        # giving a title to my graph
        plt.title('Earnings Graph (past 30 days)')

        # function to show the plot
        plt.legend()
        plt.show()


if __name__ == "__main__":
    #Graph().generate_graph()
    Graph().get_stats_for_last_30_days()