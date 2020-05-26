import json
import time
import traceback
import datetime as dt
from uuid import uuid4


class PointNotFoundError(Exception):
    pass


class PointSaveError(Exception):
    pass


class NodeNotFoundError(Exception):
    pass


class NodeSaveError(Exception):
    pass


class NodeSerializationError(Exception):
    pass


class BaseDataProxy():
    PointNotFoundError = PointNotFoundError
    PointSaveError = PointSaveError
    NodeNotFoundError = NodeNotFoundError
    NodeSaveError = NodeSaveError
    NodeSerializationError = NodeSerializationError

    def __init__(self, *args, **kwargs):
        pass


class RedisProxy(BaseDataProxy):
    def __init__(self, redis):
        super().__init__()
        self.redis = redis

    def get_node_key(self, node_uuid):
        return f'NODE-{node_uuid}'

    def get_node_stream_key(self, node_uuid):
        return f'NODE-STREAM-{node_uuid}'

    def get_node_signal_key(self, node_uuid):
        return f'NODE-SIGNAL-{node_uuid}'

    def get_node_points_key(self, node_uuid):
        return f'NODE_POINTS-{node_uuid}'

    def load_node(self, node_uuid):
        node_key = self.get_node_key(node_uuid)

        if not self.redis.exists(node_key):
            raise self.NodeNotFoundError('Node not found: %s' % node_uuid)

        node_json = self.redis.get(node_key)

        try:
            node_def = json.loads(node_json)
        except Exception as e:
            # TODO: Setup a proper log sink
            traceback.print_exc()
            raise self.NodeSerializationError('Node load failed: %s' % e)

        return node_def

    def save_node(self, node):
        node_def = node.serialize()
        node_key = self.get_node_key(node.uuid)

        try:
            node_json = json.dumps(node_def)
            result = self.redis.set(node_key, node_json)
            if not result:
                raise self.NodeSaveError(f'Redis error during node save: {result}')
        except self.NodeSaveError:
            raise
        except Exception as e:
            # TODO: Setup a proper log sink
            traceback.print_exc()
            raise self.NodeSaveError(f'Node save failed: {e}')

        return node

    def delta(self, action, **kwargs):
        # Add to stream directly or else exec callback / trigger event
        if action in ('AddPoint', 'UpdatePoint'):
            node_uuid = kwargs['node_uuid']
            point_uuid = kwargs['point_uuid']
            timestamp = kwargs['timestamp']

            stream_key = self.get_node_stream_key(node_uuid)
            self.redis.xadd(stream_key, {
                'action': action,
                'point_uuid': point_uuid,
                'timestamp': timestamp
            })

        elif action == 'NodeSignal':
            node_uuid = kwargs['node_uuid']
            wave_func = kwargs['wave_func']

            signal_key = self.get_node_signal_key(node_uuid)
            keyval = {}
            keyval['wave_func'] = json.dumps(wave_func)
            self.redis.xadd(signal_key, keyval, maxlen=1, approximate=False)

        elif action == 'AddOutgoingConnection':
            node_uuid = kwargs['node_uuid']
            outgoing_node_uuid = kwargs['outgoing_node_uuid']
            timestamp = time.time()

            stream_key = self.get_node_stream_key(node_uuid)
            self.redis.xadd(stream_key, {
                'action': action,
                'outgoing_node_uuid': outgoing_node_uuid,
                'timestamp': timestamp
            })

        elif action == 'AddIncomingConnection':
            node_uuid = kwargs['node_uuid']
            incoming_node_uuid = kwargs['incoming_node_uuid']
            timestamp = time.time()

            stream_key = self.get_node_stream_key(node_uuid)
            self.redis.xadd(stream_key, {
                'action': action,
                'incoming_node_uuid': incoming_node_uuid,
                'timestamp': timestamp
            })

        else:
            raise NotImplementedError('Delta not implemented for %s' % action)

    def get_node_history(self, node,
                         anchor_timestamp=None,
                         window=None,
                         limit=None):

        if not anchor_timestamp:
            anchor_timestamp = time.time()

        past_timestamp = '-inf'
        if window:
            past_timestamp = anchor_timestamp - window

        node_points_key = self.get_node_points_key(node.uuid)
        query_result = self.redis.zrevrangebyscore(node_points_key, anchor_timestamp,
                                                   past_timestamp, withscores=True)

        result = []
        for point_uuid, point_timestamp in query_result:
            result.append({
                'uuid': point_uuid,
                'timestamp_epoch': point_timestamp,
                'timestamp_utc': dt.datetime.fromtimestamp(point_timestamp, dt.timezone.utc)
            })

        return result

    def create_point(self, node, timestamp):
        point_uuid = str(uuid4())
        node_points_key = self.get_node_points_key(node.uuid)
        result = self.redis.zadd(node_points_key, dict([(point_uuid, timestamp)]))
        if result != 1:
            raise self.PointSaveError('Failed to add point to node via redis')

        self.delta('AddPoint', node_uuid=node.uuid, point_uuid=point_uuid, timestamp=timestamp)
        return point_uuid

    def get_point(self, node_uuid, point_uuid):
        node_points_key = self.get_node_points_key(node_uuid)

        try:
            timestamp_epoch = self.redis.zscore(node_points_key, point_uuid)
            if not timestamp_epoch:
                raise self.PointNotFoundError('Point not found')
        except self.PointNotFoundError:
            raise
        except Exception as e:
            # TODO: Setup a proper log sink
            traceback.print_exc()
            raise self.PointNotFoundError(f'Point load failed: {e}')

        return timestamp_epoch

    def update_point(self, point):
        node_points_key = self.get_node_points_key(point.node_uuid)
        timestamp = point.timestamp_epoch

        try:
            self.redis.zadd(node_points_key, dict([(point.uuid, timestamp)]))
        except Exception as e:
            # TODO: Setup a proper log sink
            traceback.print_exc()
            raise self.PointSaveError(f'Point save failed: {e}')
        else:
            self.delta('UpdatePoint',
                       node_uuid=point.node_uuid,
                       point_uuid=point.uuid,
                       timestamp=timestamp)

        return point
