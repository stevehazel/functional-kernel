import time
import math
import traceback
from uuid import uuid4
from copy import deepcopy

from point import Point
from wave_func import WaveFunc


class NodeNotSavedError(Exception):
    pass


class GraphIntegrityError(Exception):
    pass


class GraphTraversalError(Exception):
    pass


class Node():
    '''
    Construct a new Node, the backbone of the data structure.

    :param data_proxy:
    :param uuid: uuid as produced by str(uuid4())
    :param load: If True, load now. Otherwise must call load().
    :returns: Node
    :raises BaseDataProxy.NodeNotFoundError: If create=False and load=True but the ID is not
                found in the data layer.
            BaseDataProxy.NodeSerializationError:
    '''

    NodeNotSavedError = NodeNotSavedError
    GraphIntegrityError = GraphIntegrityError

    def __init__(self, data_proxy, uuid=None, attributes=None, load=True, create=False):
        self.data_proxy = data_proxy
        self.saved = False
        self.dirty = True
        self.loaded = False
        self.dirty = False

        self.incoming = []
        self.outgoing = []
        self.synthesis = None

        if not attributes or type(attributes) is not dict:
            attributes = {}
        self.attributes = attributes

        if not uuid:
            self.uuid = str(uuid4())
        else:
            self.uuid = uuid
            if create:
                # TODO: Check that the UUID doesn't already exist
                self.save()
            elif load:
                self.load()

    def __repr__(self):
        return '<Node %s>' % self.uuid

    def load(self):
        '''
        Call the data proxy to retrieve the node details and set object state

        :returns: dict
        :raises BaseDataProxy.NodeNotFoundError:
                BaseDataProxy.NodeSerializationError:
        '''

        node_def = self.data_proxy.load_node(self.uuid)

        self.incoming = node_def['incoming']
        self.outgoing = node_def['outgoing']
        self.synthesis = node_def['synthesis']
        self.attributes = node_def['attributes']

        self.loaded = True
        self.saved = True
        self.dirty = False

        return node_def

    def save(self):
        '''
        Call the data proxy to persist the current state

        :returns: None
        :raises BaseDataProxy.NodeSaveError: Generally a problem with the data layer.
        '''

        self.data_proxy.save_node(self)
        self.saved = True
        self.dirty = False

    def serialize(self):
        return {
            'uuid': self.uuid,
            'synthesis': self.synthesis,
            'outgoing': self.outgoing[:],
            'incoming': self.incoming[:],
            'attributes': deepcopy(self.attributes)
        }

    def connect_to(self, node):
        '''
        Create and persist a bidirectional outgoing connection to another node

        :returns: None
        :raises NodeNotSavedError: One of the nodes has not been saved
        '''

        # NOTE: For a bit of safety until atomic transactions span multiple nodes, enforce that
        # nodes must be already saved.
        if not self.saved or self.dirty:
            raise self.NodeNotSavedError('Current node must be saved')

        if not node.saved or node.dirty:
            raise self.NodeNotSavedError('Destination node must be saved')

        if self.uuid == node.uuid:
            raise self.GraphIntegrityError('Cannot connect to self')

        self.add_outgoing(node)
        node.add_incoming(self)

        # TODO: Wrap in a redis transaction to ensure atomicity
        # TODO: Defer the delta output (below) until transaction suceeds
        self.save()
        node.save()

    def connect_from(self, node):
        '''
        The reverse of connect_to(), with identical signature.
        '''

        node.connect_to(self)

    def get_outgoing(self):
        outgoing_nodes = []
        for outgoing_node_uuid in self.outgoing:
            outgoing_node = Node(self.data_proxy, uuid=outgoing_node_uuid, load=True)
            outgoing_nodes.append(outgoing_node)

        return outgoing_nodes

    def add_outgoing(self, node, emit_delta=True):
        if node.uuid in self.outgoing:
            return

        self.outgoing.append(node.uuid)
        if emit_delta:
            self.data_proxy.delta('AddOutgoingConnection',
                                  node_uuid=self.uuid,
                                  outgoing_node_uuid=node.uuid)

    def add_incoming(self, node, emit_delta=True):
        if node.uuid in self.incoming:
            return

        self.incoming.append(node.uuid)
        if emit_delta:
            self.data_proxy.delta('AddIncomingConnection',
                                  node_uuid=self.uuid,
                                  incoming_node_uuid=node.uuid)

    def query_outgoing(self, seen=None):
        '''
        Traverse the graph to retrieve the set of nodes linked by outgoing connections. Has basic
            cycle prevention.

        :returns: dict of node_uuid -> Node
        :raises GraphTraversalError: A wrapper around the Node constructor, typically representing
            a NodeNotFoundError or NodeSerializationError
        '''

        if not seen:
            seen = set([])

        result = {}
        result[self.uuid] = self

        for outgoing_node_uuid in self.outgoing:
            if seen and outgoing_node_uuid in seen:
                continue

            try:
                # NOTE: While it's clearly inefficient to make a round-trip call for each Node,
                # right now the primary concern is whether or not this design achieves the
                # high-level goal.
                outgoing_node = Node(self.data_proxy, uuid=outgoing_node_uuid, load=True)
            except Exception as e:
                # TODO: Setup a proper log sink
                traceback.print_exc()
                raise self.GraphTraversalError(e)
            else:
                result[outgoing_node_uuid] = outgoing_node
                seen.add(outgoing_node_uuid)

                outgoing_result = outgoing_node.query_outgoing(seen=seen)
                result.update(outgoing_result)

        return result

    def set_attribute(self, key, value, save=False):
        self.attributes[key] = value
        self.dirty = True

        if save:
            self.save()

    def attr(self, key):
        return self.attributes.get(key)

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

        if time_since is None:
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
        :returns: list of points serialized as dicts
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
            self.data_proxy.delta('NodeSignal',
                                  node_uuid=self.uuid,
                                  wave_func=wave_func.serialize())
        return Point(self.data_proxy, self.uuid,
                     uuid=point_uuid,
                     timestamp_epoch=timestamp_epoch,
                     load=False)

    def get_point(self, point_uuid):
        timestamp_epoch = self.data_proxy.get_point(self.uuid, point_uuid)
        return Point(self.data_proxy, self.uuid,
                     uuid=point_uuid,
                     timestamp_epoch=timestamp_epoch,
                     load=False)
