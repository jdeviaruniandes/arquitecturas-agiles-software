from datetime import datetime, timezone
from flask import Flask, request, jsonify
from influxdb import InfluxDBClient
import requests

app = Flask(__name__)
internal_key = "internal_key"

incident_data = {
    1: {
        "company": 1,
        "title": "Incident Example"
    },
    2: {
        "company": 1,
        "title": "Incident Same Company"
    },
    3: {
        "company": 2,
        "title": "Incident Another company"
    }
}

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

@app.route('/incident/<int:incident_id>', methods=['GET'])
def get_incident(incident_id):
    headers = request.headers

    if not headers.has_key('Authorization'):
        return "Error", 403

    if incident_id not in incident_data:
        db.write_points(get_json("incident", 404))
        return 'User not found', 404

    incident = incident_data[incident_id]

    url = "http://auth/verify"
    data = {
        "token": headers.get('Authorization'),
    }
    headers = {
        "internal-key": internal_key
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        return "Error", response.status_code

    body = response.json()
    if body["company"] != incident["company"]:
        return "Error", 403

    return jsonify(incident)

if __name__ == '__main__':
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)