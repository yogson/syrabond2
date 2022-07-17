import json


class JsonToChannels:

    def __init__(self, **kwargs):
        pass

    def __call__(self, *args, raw_state=None, **kwargs):
        if raw_state:
            return json.loads(raw_state)
