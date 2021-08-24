from json import JSONDecodeError

import logging
import os
import sqlite3
from datetime import datetime
from datetime import timedelta

from api import API


class Stats:

    def __init__(self):
        self.conn = sqlite3.connect(os.path.dirname(os.path.dirname(__file__)) + '/data.db')
        self.curs = self.conn.cursor()
        self.table_exists()

    def table_exists(self):
        data = self.curs.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='stats' ''')
        if data.fetchone()[0] != 1:
            logging.info("Creating a new table: stats")
            self.curs.execute(''' create table stats
                                (
                                    id   INTEGER      not null
                                        primary key autoincrement,
                                    node_public_key VARCHAR(128),
                                    node_description VARCHAR(128),
                                    date VARCHAR(128),
                                    earned_tokens VARCHAR(128)
                                );
                            ''')
            self.conn.commit()

    @staticmethod
    def get_dates_in_last_30_days():
        today_date = datetime.today()
        date_list = [(today_date - timedelta(days=x+1)).strftime("%Y-%m-%d") for x in range(30)]
        return date_list

    def store_nodes_earnings_stats(self):
        dates = self.get_dates_in_last_30_days()

        try:
            for current_date in dates:
                if self.curs.execute(''' SELECT count(id) FROM stats 
                                         WHERE date=? ''', (current_date, )).fetchone()[0] == 0:
                    next_day = (datetime.strptime(current_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                    logging.info("Sending API request for start date: " + current_date + " and end date: " + next_day)

                    # sending the request for the given date
                    response = API().send_request_with_params(
                        "stats=true", "start_date=" + current_date, "end_date=" + next_day
                    )

                    # get data
                    for node in response['nodes']:
                        public_key = node
                        node_description = response['nodes'][node]['meta']['description']
                        date = current_date
                        earned_tokens = response['nodes'][node]['period']['total_pre_earned']

                        self.curs.execute(''' INSERT INTO stats(node_public_key, node_description, date, earned_tokens)
                                              VALUES (?, ?, ?, ?) ''',
                                          (public_key, node_description, date, earned_tokens))

                    self.conn.commit()

        except JSONDecodeError:
            logging.error("Unable to parse API response")
        finally:
            self.conn.close()


if __name__ == '__main__':
    Stats().store_nodes_earnings_stats() # TODO remove
