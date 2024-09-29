import time
from datetime import datetime, timezone
import sys
from flask import Flask, request, jsonify
from influxdb import InfluxDBClient
import requests

app = Flask(__name__)
internal_key = "internal_key"
ban_time = 30

incident_data = {
    1: {
        "company": 1,
        "title": "Incident Example",
        "type": "Private"
    },
    2: {
        "company": 1,
        "title": "Incident Same Company",
        "type": "Restricted"
    },
    3: {
        "company": 2,
        "title": "Incident Another company",
        "type": "Private"
    }
}

black_list = {}

db = InfluxDBClient("influxdb", 8086, 'root', 'root', 'app-client')

def get_json(measurement, status = 200):
    now = datetime.now(timezone.utc)
    return [
        {
            "measurement": "app_"+measurement,
            "tags": {
                "type": "information",
                "status": "UserClient: " + str(status)
            },
            "time": now,
            "fields": {
                "status": status
            }
        }
    ]

@app.route('/incidents/<int:incident_id>', methods=['GET'])
def get_incident(incident_id):
    headers = request.headers
    if request.remote_addr in black_list and time.time() < black_list[request.remote_addr]:
        db.write_points(get_json("report_incident", 403))
        return "Access Blocked" + str(black_list[request.remote_addr] - time.time()), 403

    if headers.get('Authorization') is None:
        return "Error, require token", 403

    url = "http://auth-api/auth/verify"
    data = {
        "token": headers.get('Authorization'),
    }
    headers = {
        "internal-key": internal_key
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        black_list[request.remote_addr] = time.time() + ban_time
        db.write_points(get_json("report_incident", 403))
        return "Error, Invalid token", response.status_code

    if incident_id not in incident_data:
        db.write_points(get_json("read_incident", 404))
        return 'User not found', 404

    incident = incident_data[incident_id]

    body = response.json()
    print(body, file=sys.stderr)
    if body["company"] != incident["company"]:
        black_list[request.remote_addr] = time.time() + ban_time
        db.write_points(get_json("report_incident", 403))
        return "Error, Invalid Company", 403

    if incident["type"] == "Restricted" and body["role"] != "Admin":
        black_list[request.remote_addr] = time.time() + ban_time
        db.write_points(get_json("report_incident", 403))
        return "Error, Insufficient permissions", 403

    db.write_points(get_json("read_incident", 200))
    return jsonify(incident)

if __name__ == '__main__':
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)