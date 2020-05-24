from uuid import uuid4
import datetime as dt
import time


class Point():
    '''The Point class. Represents fundamental data.

    Construct a new Point

    :param data_proxy:
    :param uuid: uuid as produced by str(uuid4())
    :param timestamp: High resolution UTC datetime()
    :param load: If True, load now. Otherwise must call load().
    :returns: Point
    :raises PointNotFoundError:
    '''

    def __init__(self, data_proxy, node_uuid, uuid=None,
                 timestamp_epoch=None, timestamp_utc=None, load=True):
        self.data_proxy = data_proxy

        self.node_uuid = node_uuid
        self.uuid = uuid
        self.timestamp_epoch = timestamp_epoch
        self.timestamp_utc = timestamp_utc

        self.saved = False
        self.loaded = False

        if not uuid:
            self.uuid = str(uuid4())

            if not self.timestamp_epoch:
                self.timestamp_epoch = time.time()

            if not self.timestamp_utc:
                self.timestamp_utc = dt.datetime.fromtimestamp(self.timestamp_epoch, dt.timezone.utc)

            self.save()
        else:
            if load:
                self.load()

    def __repr__(self):
        return '<Point %s>' % self.uuid

    def save(self):
        '''
        Call the data proxy to persist the current object state

        :returns: dict
        :raises PointNotFoundError:
        '''

        self.data_proxy.update_point(self)
        self.saved = True

        return self

    def load(self):
        '''
        Call the data proxy to retrieve the point details and set object state

        :returns: dict
        :raises PointNotFoundError:
        '''

        timestamp_epoch = self.data_proxy.get_point(self.node_uuid, self.uuid)

        self.timestamp_epoch = timestamp_epoch
        self.timestamp_utc = dt.datetime.fromtimestamp(self.timestamp_epoch, dt.timezone.utc)
        self.loaded = True
        self.saved = True

        return self

    def serialize(self):
        return {
            'uuid': self.uuid,
            'timestamp_epoch': self.timestamp_epoch,
            'timestamp_utc': self.timestamp_utc
        }
