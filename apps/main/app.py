import concurrent.futures
import os
import random

import requests

from datetime import datetime, timezone
from time import time, sleep
from flask import Flask, request, Response
from flask_restful import Api, Resource
from influxdb import InfluxDBClient


app = Flask(__name__)
api = Api(app)
db = InfluxDBClient("influxdb", 8086, 'root', 'root', 'app-client')
failure_timer = time() + 240  + random.randint(60, 180)  # 5 minutes in seconds

def read_hostname():
    """Reads the hostname from the /etc/hostname file."""
    try:
        with open("/etc/hostname", "r") as f:
            hostname = f.read().strip()
            return hostname
    except FileNotFoundError:
        print("Error: /etc/hostname file not found.")
        return None

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
    return retry_request(url, delay * 1.25)

def make_simultaneous_requests(urls):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(retry_request, url, 0.25) for url in urls]
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
            response = Response("Error Status", mimetype='text/plain', status = 500)
            response.headers['X-Host-ID'] = host_id
            db.write_points(get_json("status", 500))
            return response

        response = Response("Success Status", status = 200, mimetype='text/plain')
        response.headers['X-Host-ID'] = host_id
        db.write_points(get_json("status", 200))
        return response

api.add_resource(ApiRoute, '/call/income')
api.add_resource(StatusRoute, '/status')

if __name__ == '__main__':
    host_id = read_hostname()
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)