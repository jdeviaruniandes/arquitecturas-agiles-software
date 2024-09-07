import concurrent.futures
from venv import logger

import requests
from datetime import datetime, timezone
from time import time, sleep
from flask import Flask, request, Response
from flask_restful import Api, Resource
from influxdb import InfluxDBClient

app = Flask(__name__)
api = Api(app)
db = InfluxDBClient("influxdb", 8086, 'root', 'root', 'app-client')
duration_time = {}

def read_hostname():
    """Reads the hostname from the /etc/hostname file."""
    try:
        with open("/etc/hostname", "r") as f:
            hostname = f.read().strip()
            return hostname
    except FileNotFoundError:
        print("Error: /etc/hostname file not found.")
        return None


def get_json(name, status = 200, duration = 0):
    now = datetime.now(timezone.utc)
    return [
        {
            "measurement": "app_response",
            "tags": {
                "status": name + ": " + str(status)
            },
            "time": now,
            "fields": {
                "status": status,
                "duration": duration
            }
        }
    ]


def retry_request(url, delay):

    response = requests.get(url)
    if response.status_code == 200:
        return response

    sleep(delay)
    return retry_request(url, delay * 1.15)

def make_simultaneous_requests(urls, request_id):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(retry_request, url, 0.3) for url in urls]
        return [future.result() for future in futures], request_id


def make_simultaneous_requests_sync(urls, request_id):
    results = []
    for url in urls:
        success = False
        attempts = 0
        while not success and attempts < 3:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    results.append(response.json())
                    success = True
                else:
                    print(f"Error: {response.status_code} for URL {url}")
            except Exception as e:
                print(f"Error: {e} for URL {url}")
            attempts += 1

    return results, request_id


class ApiRoute(Resource):

    def get(self):
        base_url = "http://nginx/information"
        request_id = request.headers.get('X-Request-Id')
        duration_time[request_id] = {}
        urls = [
            base_url+"/user",
            base_url+"/social",
            base_url+"/products",
        ]

        duration_time[request_id]["initial"] = time()

        results, request_id = make_simultaneous_requests_sync(urls, request_id)

        duration_time[request_id]["final"] = time()
        duration_time[request_id]["total"] = int(duration_time[request_id]["final"] - duration_time[request_id]["initial"])
        logger.error(duration_time[request_id]["total"])

        db.write_points(get_json("Api Call", 200, duration_time[request_id]["total"]))
        duration_time.pop(request_id)
        return "Success Call ", 200

class StatusRoute(Resource):

    def get(self):

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