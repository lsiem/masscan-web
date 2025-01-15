from masscan_web import app, socketio

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=12000, allow_unsafe_werkzeug=True)