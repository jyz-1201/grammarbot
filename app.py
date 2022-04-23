from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

class HelloWorld(Resource):
    def get(self):
        return {'hello': "this is an invocation of get method"}
    def put(self):
        return {"put_hello": request.form['username']}
    def post(self):
        return {"posted_hello": "res"}

api.add_resource(HelloWorld, '/login')

if __name__ == "__main__":
    app.run()
