import requests
import logging

from datetime import datetime, timezone
from time import time, sleep
from influxdb import InfluxDBClient

db = InfluxDBClient("influxdb", 8086, 'root', 'root', 'app-monitor')

def get_json(host_id, status = 200):
    now = datetime.now(timezone.utc)
    return [
        {
            "measurement": "app_status",
            "tags": {
                "app": "monitor",
                "status": "monitor" + ": " + str(status),
                "host": host_id
            },
            "time": now,
            "fields": {
                "status": status
            }
        }
    ]

base_url = "http://nginx/status"

if __name__ == '__main__':
    db.create_database('app-monitor')
    sleep(1)
    while True:
        response = requests.get(base_url)
        host_id = "N/A"

        if "X-Host-ID" in response.headers:
            host_id = response.headers["X-Host-ID"]

        try:
            db.write_points(get_json(host_id, response.status_code))
        except:
            logging.info("Write code")

        sleep(2)
