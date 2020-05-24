#!/usr/bin/python

from gevent import monkey
monkey.patch_all()

import time
import json
from threading import Thread
from redis import StrictRedis
from uuid import uuid4
from flask import Flask, request
from flask_socketio import SocketIO, emit, disconnect, join_room, leave_room

from util import is_uuid

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

redis = StrictRedis(host='redis', db=0)


class SignalInterface(object):
    def __init__(self, redis, socketio):
        self.redis = redis
        self.socketio = socketio

        self.namespace_map = {}
        self.signal_listeners = {}

    def listen(self, node_uuid, debug=False):
        signal_listener = self.signal_listeners.get(node_uuid)
        if not signal_listener:
            signal_listener = SignalListener(self.socketio, self.redis, node_uuid, self.send_signal, debug=debug)
            signal_listener.start()
            self.signal_listeners[node_uuid] = signal_listener
        return signal_listener

    def get_listener(self, node_uuid):
        return self.signal_listeners.get(node_uuid)

    def get_namespace(self, node_uuid):
        key = node_uuid
        return self.namespace_map.get(key)

    def set_namespace(self, node_uuid, namespace):
        key = node_uuid
        self.namespace_map[key] = namespace

    def construct_message(self, node_uuid, signal=None):
        if not signal:
            listener = self.get_listener(node_uuid)
            if listener:
                signal = listener.wave_func

        if signal:
            return {
                'type': 'WaveFunc',
                'version': '0.01',
                'action': 'Update',
                'data': signal
            }

    def send_signal(self, node_uuid, signal):
        msg = self.construct_message(node_uuid, signal)
        print('msg', msg)
        if msg:
            socketio.emit('signal', msg, namespace='/signals', room=node_uuid)


class SignalListener(Thread):
    def __init__(self, socketio, redis, node_uuid, send_callback, debug=False):
        Thread.__init__(self)

        self.socketio = socketio
        self.redis = redis
        self.daemon = True
        self.node_uuid = node_uuid
        self.send_callback = send_callback
        self.debug = debug

        self.wave_func = None

    def run(self):
        debug = self.debug
        first_run = True
        last_stream_id = None

        signal_key = 'NODE-SIGNAL-%s' % self.node_uuid
        self.wave_func = None

        while True:
            if first_run:
                # Retrieve the current (latest) signal if available
                result = self.redis.xrevrange(signal_key, max='+', min='-', count=1)
                if debug:
                    print('first run', result)

                if result:
                    last_stream_id = result[0][0]
                    wave_func_json = result[0][1][b'wave_func']
                    self.wave_func = json.loads(wave_func_json)

                first_run = False
            else:
                # Block while waiting for refreshed signal

                if debug:
                    print('block on stream', last_stream_id)

                streams = {}
                streams[signal_key] = last_stream_id or '$'
                result = self.redis.xread(streams, count=1, block=0)

                if debug:
                    print('listen result', result)

                for stream_name, stream_entries in result:
                    if debug:
                        print('stream_name', stream_name)
                        print('stream_entries', stream_entries)

                    for stream_id, stream_value_dict in stream_entries:
                        wave_func_json = stream_value_dict[b'wave_func']
                        self.wave_func = json.loads(wave_func_json)
                        last_stream_id = stream_id

            print('wave_func', self.wave_func)
            self.send_callback(self.node_uuid, self.wave_func)


@socketio.on('event', namespace='/signals')
def handle_message(message):
    print(message)

    if type(message) is not dict:
        return

    msg_type = message.get('msg')
    if msg_type not in ('SignalConnectionInit', 'AddPoint'):
        print('Unknown message: %s' % msg_type)
        return

    data = message.get('data')
    if type(data) is not dict:
        return

    if msg_type == 'SignalConnectionInit':
        session_id = data.get('session_id', None)
        node_uuid = data.get('node_uuid', None)

        if not session_id:
            print('SessionID missing')
            return

        if not node_uuid or not is_uuid(node_uuid):
            print('NodeUUID required')
            return

        app.signal_interface.set_namespace(node_uuid, request.namespace)
        app.signal_interface.listen(node_uuid, debug=False)

        join_room(node_uuid)
        msg = {
            'Msg': 'SignalConnectionInit',
            'Signal': app.signal_interface.construct_message(node_uuid)
        }
        socketio.emit('control', msg, namespace='/signals', room=node_uuid)

    elif msg_type == 'AddPoint':
        session_id = data.get('session_id')
        node_uuid = data.get('node_uuid')
        client_time = float(data.get('point_time')) / 1000

        add_point(node_uuid, client_time)
        print('Added point for %s' % node_uuid)


def add_point(node_uuid, point_time=None):
    import time
    from node import Node
    from data_proxy.redis import RedisProxy

    redis_proxy = RedisProxy(redis)
    root_node = Node(redis_proxy, uuid=node_uuid, create=True)

    if not point_time:
        point_time = time.time()
    root_node.create_point(point_time)


@socketio.on('broadcast', namespace='/signals')
def handle_broadcast_message(message):
    # emit('control', {'data': message['data']}, broadcast=True)
    pass


@socketio.on('disconnect request', namespace='/signals')
def disconnect_request():
    # emit('control', {'data': 'Disconnected'})
    disconnect()


@socketio.on('connect', namespace='/signals')
def handle_connect():
    # emit('control', {'data': 'Connected'})
    print('Client connected')


@socketio.on('disconnect', namespace='/signals')
def handle_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    app.signal_interface = SignalInterface(redis, socketio)
    socketio.run(app, host='0.0.0.0', port=7011, use_reloader=False)
