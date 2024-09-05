import concurrent.futures
import requests

from datetime import datetime, timezone
from random import random
from time import time, sleep
from flask import Flask
from flask_restful import Api, Resource
from influxdb import InfluxDBClient


app = Flask(__name__)
api = Api(app)
db = InfluxDBClient("influxdb", 8086, 'root', 'root', 'app-client')
failure_timer = time() + 300  # 5 minutes in seconds

def get_json(name, status = 200):
    now = datetime.now(timezone.utc)
    return [
        {
            "measurement": "app_response",
            "tags": {
                "status": name + ": " + str(status)
            },
            "time": now,
            "fields": {
                "status": status
            }
        }
    ]


def retry_request(url, delay):

    response = requests.get(url)
    if response.status_code == 200:
        return response

    sleep(delay)
    return retry_request(url, delay * 2)

def make_simultaneous_requests(urls):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(retry_request, url, 1) for url in urls]
        return [future.result() for future in futures]

class ApiRoute(Resource):

    def get(self):
        if time() > failure_timer:
            db.write_points(get_json("Api Call", 500))
            return "Error Status", 500

        base_url = "http://nginx/information"
        urls = [
            base_url+"/user",
            base_url+"/social",
            base_url+"/products",
        ]

        make_simultaneous_requests(urls)

        db.write_points(get_json("Api Call", 200))
        return "Success Call ", 200

class StatusRoute(Resource):

    def get(self):
        if time() > failure_timer:
            db.write_points(get_json("status", 500))
            return "Error Status", 500

        db.write_points(get_json("status"))
        return "Success Status", 200

api.add_resource(ApiRoute, '/call/income')
api.add_resource(StatusRoute, '/status')

if __name__ == '__main__':
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)