from datetime import datetime, timezone
from flask import Flask, request
from influxdb import InfluxDBClient
import bcrypt
import jwt
import re

app = Flask(__name__)
encrypt_key = "secret"
internal_key = "internal_key"

user_data = {
    1: {
        "company": 1,
        "password": "$2a$12$y99Z97tBEuNabtQbVQ4w..UCia9RygeIN0uMFowuvGa1X/jJu8hw2",
        "role": "Operator"
    },
    2: {
        "company": 1,
        "password": "$2a$12$xaPqNv0JS.oaFR3yPEMFDO.IR6nzW/Y1brSMj1sFskSUbtz7M/0ii",
        "role": "Admin"
    },
    3: {
        "company": 2,
        "password": "$2a$12$RkMZuIK5gREjQdvxpnm5MeHIe.9vBkySS4GrBlRfszhLPqYdviHOK",
        "role": "Operator"
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

@app.route('/auth/verify', methods=['POST'])
def verify():
    headers = request.headers
    data = request.get_json()
    token = data.get('token')

    if headers.get('internal-key') != internal_key:
        return "Error Internal Key", 403

    try:
        decoded = jwt.decode(re.sub(r'^Bearer\s+', '', token), encrypt_key, algorithms="HS256")
        db.write_points(get_json("authorization"))
        return decoded, 200
    except jwt.InvalidTokenError:
        return "Error Invalid Token", 401


@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    password = data.get('password')
    user = data.get('user')


    if user not in user_data:
        db.write_points(get_json("authorization", 404))
        return 'User not found', 404

    password_bytes = password.encode('utf-8')
    result = bcrypt.checkpw(password_bytes, user_data[user]["password"].encode('utf-8'))

    if result:
        db.write_points(get_json("authorization"))
        encoded_jwt = jwt.encode({"user": user, "company": user_data[user]["company"], "role": user_data[user]["role"]}, encrypt_key, algorithm="HS256")
        return encoded_jwt, 200

    db.write_points(get_json("authorization", 401))
    return 'Error', 401



if __name__ == '__main__':
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)