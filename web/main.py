from flask import Flask
from flask import request

app = Flask(__name__)

@app.route("/login", methods=['GET'])
def login():
    print(request.args.get('code'))
    print(request.args.get('state'))
    return "Thanks for the password, suckas!"

if __name__ == '__main__':
   app.run(debug=True, port=8080)