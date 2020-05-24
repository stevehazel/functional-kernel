import time
import math
from uuid import uuid4

from point import Point
from wave_func import WaveFunc


class Node():
    '''
    Construct a new Node, the backbone of the data structure.

    :param data_proxy:
    :param uuid: uuid as produced by str(uuid4())
    :param load: If True, load now. Otherwise must call load().
    :returns: Node
    :raises NodeNotFoundError:
    '''

    def __init__(self, data_proxy, uuid=None, load=True, create=False):
        self.data_proxy = data_proxy
        self.saved = False
        self.loaded = False
        self.dirty = False

        self.incoming = []
        self.outgoing = []
        self.synthesis = None

        if not uuid:
            self.uuid = str(uuid4())
        else:
            self.uuid = uuid
            if create:
                self.save()
            elif load:
                self.load()

    def __repr__(self):
        return '<Node %s>' % self.uuid

    def load(self):
        '''
        Call the data proxy to retrieve the node details and set object state

        :returns: dict
        :raises NodeNotFoundError:
        '''

        node_def = self.data_proxy.load_node(self.uuid)

        self.incoming = node_def['incoming']
        self.outgoing = node_def['outgoing']
        self.synthesis = node_def['synthesis']

        self.loaded = True
        self.saved = True

        return node_def

    def save(self):
        '''
        Call the data proxy to persist the current state

        :returns: ??
        :raises Exception:
        '''

        self.data_proxy.save_node(self)
        self.saved = True

    def serialize(self):
        return {
            'uuid': self.uuid,
            'synthesis': self.synthesis,
            'outgoing': self.outgoing[:],
            'incoming': self.incoming[:],
        }

    def get_period(self, anchor_timestamp=None, window=None):
        if not anchor_timestamp:
            anchor_timestamp = math.ceil(time.time())

        if not window:
            window = (86400 * 30)

        def calc_avg_interval(pts, anchor_time=None):
            # pts sorted high to low
            intervals = []
            last_time = anchor_time
            for point_time in pts:
                if last_time:
                    intervals.append(last_time - point_time)
                last_time = point_time

            return sum(intervals) / len(intervals)

        points = self.get_history(anchor_timestamp=anchor_timestamp, window=window)

        pts = [p['timestamp_epoch'] for p in points]
        pts.sort(reverse=True)  # Sort largest (newest) to smallest (oldest)
        pts = pts[:10]

        recent_interval_5 = 1
        last_event_time = None
        score_interval = 0
        if len(pts) > 1:
            recent_interval_5 = calc_avg_interval(pts[:5])

            score_interval = recent_interval_5
            last_event_time = pts[0]

        time_since = None
        if last_event_time:
            time_since = anchor_timestamp - last_event_time

        return score_interval, time_since

    def get_score_func(self, anchor_timestamp=None, window=None, serialized=False):
        if not anchor_timestamp:
            anchor_timestamp = math.ceil(time.time())

        if not window:
            window = (86400 * 30)

        period, time_since = self.get_period(anchor_timestamp=anchor_timestamp,
                                             window=window)

        if not time_since:
            return None

        wave_func_def = {
            'ref_time': anchor_timestamp - time_since,
            'period': period * 1.0,
            'decay': 0.2,
            'funcs': [{
                'func': 'sin',
                'phase': 0
            }]
        }
        wave_func = WaveFunc(serialized=wave_func_def)
        if serialized:
            return wave_func.serialize()
        return wave_func

    def get_history(self, anchor_timestamp=None, window=None, limit=None):
        '''
        Retrieve points via explicit timestamp, range, and limit

        :param anchor_timestamp: newest possible point
        :param window: range in seconds
        :param limit: maximum number of points to return, newest first
        :returns: list of points
        :raises Exception: raises an exception
        '''

        return self.data_proxy.get_node_history(self, anchor_timestamp=anchor_timestamp,
                                                window=window,
                                                limit=limit)

    def create_point(self, timestamp_epoch=None):
        if not timestamp_epoch:
            timestamp_epoch = time.time()

        point_uuid = self.data_proxy.create_point(self, timestamp_epoch)
        wave_func = self.get_score_func()
        if wave_func:
            self.data_proxy.delta('NodeSignal', node_uuid=self.uuid, wave_func=wave_func.serialize())
        return Point(self.data_proxy, self.uuid, uuid=point_uuid,
                     timestamp_epoch=timestamp_epoch, load=False)

    def get_point(self, point_uuid):
        timestamp_epoch = self.data_proxy.get_point(self.uuid, point_uuid)
        return Point(self.data_proxy, self.uuid, uuid=point_uuid,
                     timestamp_epoch=timestamp_epoch, load=False)
