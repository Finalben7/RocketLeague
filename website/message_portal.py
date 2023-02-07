"""
Author: Niklaas Cotta
Last Updated: 2/2/23
Base: https://www.youtube.com/watch?v=whEObh8waxg
Tunnelling: https://www.youtube.com/watch?v=hs7GLsHQCPQ
Matchmaking: https://youtu.be/_08lsRxqnm4
"""

from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET'] = "secret!123"  # FIXME
socketio = SocketIO(app, cors_allowed_origins="*")


@socketio.on('message')
def handle_message(message):
    print(f"Recieved message: {message}")
    if message != "User connected!":
        send(message, broadcast=True) 


@app.route('/match')
def index():
    return render_template("match.html")


if __name__ == "__main__":
    socketio.run(app, host="localhost")