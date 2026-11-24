import os
import warnings
from flask import Flask, request
from flask_socketio import SocketIO, emit

# Eventlet deprecation warning සඟවා තැබීමට
warnings.filterwarnings("ignore", category=DeprecationWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kiyasha_remote_signaling_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# { "482910334": {"sid": "socket_id", "pin": "123456"} }
ONLINE_PEERS = {}

@app.route('/')
def index():
    return "Kiyasha Remote Signaling Server is Online!"

@socketio.on('register_peer')
def handle_register_peer(data):
    peer_id = str(data.get('peer_id', '')).replace(' ', '').strip()
    pin = str(data.get('pin', '')).strip()
    if not peer_id:
        return
    ONLINE_PEERS[peer_id] = {
        'sid': request.sid,
        'pin': pin
    }
    emit('peer_registered', {'peer_id': peer_id})

@socketio.on('update_pin')
def handle_update_pin(data):
    peer_id = str(data.get('peer_id', '')).replace(' ', '').strip()
    pin = str(data.get('pin', '')).strip()
    if peer_id in ONLINE_PEERS:
        ONLINE_PEERS[peer_id]['pin'] = pin

@socketio.on('request_connection')
def handle_request_connection(data):
    target_id = str(data.get('target_id', '')).replace(' ', '').strip()
    pin = str(data.get('pin', '')).strip()
    requester_id = str(data.get('requester_id', '')).replace(' ', '').strip()

    target = ONLINE_PEERS.get(target_id)
    if not target:
        emit('connection_failed', {'reason': 'Target ID is offline or invalid.'})
        return

    if target['pin'] != pin:
        emit('connection_failed', {'reason': 'Invalid Session PIN / Password.'})
        return

    emit('incoming_request', {
        'requester_sid': request.sid,
        'requester_id': requester_id
    }, room=target['sid'])

@socketio.on('respond_connection')
def handle_respond_connection(data):
    requester_sid = data.get('requester_sid')
    accepted = bool(data.get('accepted', False))
    allow_control = bool(data.get('allow_control', True))

    if accepted:
        emit('connection_accepted', {
            'host_sid': request.sid,
            'allow_control': allow_control
        }, room=requester_sid)
        emit('session_ready', {
            'requester_sid': requester_sid,
            'allow_control': allow_control
        })
    else:
        emit('connection_failed', {'reason': 'Remote user rejected the request.'}, room=requester_sid)

@socketio.on('forward_payload')
def handle_forward_payload(data):
    target_sid = data.get('target_sid')
    payload = data.get('payload')
    if target_sid and payload is not None:
        emit('incoming_payload', {
            'from_sid': request.sid,
            'payload': payload
        }, room=target_sid)

@socketio.on('disconnect')
def handle_disconnect():
    to_remove = [pid for pid, info in ONLINE_PEERS.items() if info['sid'] == request.sid]
    for pid in to_remove:
        del ONLINE_PEERS[pid]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)