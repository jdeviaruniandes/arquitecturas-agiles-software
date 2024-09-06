from datetime import datetime, timezone
from random import random


from flask import Flask
from flask_restful import Api, Resource
from influxdb import InfluxDBClient


app = Flask(__name__)
api = Api(app)
db = InfluxDBClient("influxdb", 8086, 'root', 'root', 'app-client')

def get_json(path, status = 200):
    now = datetime.now(timezone.utc)
    return [
        {
            "measurement": "app_response",
            "tags": {
                "resource": path,
                "type": "information",
                "status": "UserClient: " + str(status)
            },
            "time": now,
            "fields": {
                "status": status
            }
        }
    ]


class FakeRoute(Resource):
    def get(self, path):
        failure = random()
        if failure > 0.2:
            db.write_points(get_json(path))
            return "Success: " + path, 200

        db.write_points(get_json(path, 500))
        return "Error!", 500

api.add_resource(FakeRoute, '/information/<path:path>')

if __name__ == '__main__':
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)