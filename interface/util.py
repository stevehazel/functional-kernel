import re

uuid4hex = re.compile('[0-9a-f]{8}(\-[0-9a-f]{4}){3}\-[0-9a-f]{12}\Z', re.I)


def is_uuid(u):
    return u and type(u) in (str, bytes) and uuid4hex.match(u)
