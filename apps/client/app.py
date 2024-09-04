from random import random

from flask import Flask
from flask_restful import Api, Resource

app = Flask(__name__)
api = Api(app)

class FakeRoute(Resource):
    def get(self, path):
        failure = random()
        if failure > 0.2:
            return "Success: " + path, 200

        return "Error!", 500

api.add_resource(FakeRoute, '/information/<path:path>')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)