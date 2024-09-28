from datetime import datetime, timezone
from flask import Flask, request
from influxdb import InfluxDBClient
import bcrypt
import jwt

app = Flask(__name__)
encrypt_key = "secret"
user_data = {
    1: {
        "company": 1,
        "password": "$2a$12$y99Z97tBEuNabtQbVQ4w..UCia9RygeIN0uMFowuvGa1X/jJu8hw2"
    },
    2: {
        "company": 2,
        "password": "$2a$12$RkMZuIK5gREjQdvxpnm5MeHIe.9vBkySS4GrBlRfszhLPqYdviHOK"
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

@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    token = data.get('token')

    try:
        decoded = jwt.decode(token, encrypt_key, algorithms="HS256")
        db.write_points(get_json("authorization"))
        return decoded, 200
    except jwt.InvalidTokenError:
        return "Error", 401


@app.route('/login', methods=['POST'])
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
        encoded_jwt = jwt.encode({"user": user, "company": user_data[user]["company"]}, encrypt_key, algorithm="HS256")
        return encoded_jwt, 200

    db.write_points(get_json("authorization", 401))
    return 'Error', 401



if __name__ == '__main__':
    db.create_database('app-client')
    app.run(debug=True, host='0.0.0.0', port=80)