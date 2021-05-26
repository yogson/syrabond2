import paho.mqtt.client as mqtt
import sys
from time import sleep
from .common import config, log


class Queue:

    def __init__(self, l=()):
        self.queue = list(l)
        self.size = self.queue.__len__()

    def __repr__(self):
        return f'Queue {self.queue}'

    def enqueue(self, n):
        self.queue.insert(0, n)
        self.size += 1

    def dequeue(self):
        if self.size > 0:
            self.size -= 1
            return self.queue.pop()
        else:
            return None

    def clear(self):
        self.queue.clear()
        self.size = 0


class SingletonDecorator:
    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kwargs):
        if not self.instance:
            self.instance = self.klass(*args, **kwargs)
        return self.instance


class Mqtt:
    """
    Wrapper class for paho.mqtt.client.
    Handles connecting, subscribing, receiving and sending MQTT-messages.
    Holds the messages in own message buffer that used by other classes to get messages.
    Accepts conf.json file in config dir to get config.
    """

    def __init__(self, name, config=config, clean_session=False, handler=None):
        self.connected = False
        mqtt_config = config.get('mqtt')
        self.name = name
        self.clean_session = clean_session
        self.root = mqtt_config['object_name']
        self.broker = mqtt_config['server']
        self.ping_topic = mqtt_config['ping_topic']
        self.client = mqtt.Client(self.name, clean_session=self.clean_session)
        self.client.username_pw_set(username=mqtt_config['user'], password=mqtt_config['password'])
        self.client.on_message = self.message_to_buffer
        self.client.on_disconnect = self.on_disconnect
        self.message_buffer = Queue()
        self.external_handler = handler
        self.subscriptions = []

    def connect(self):
        try:
            print('Connecting...')
            #log('Connecting...')
            if not self.client.connect(self.broker):
                self.connected = True
        except Exception as e:
            log('Connection error: {}'.format(e), log_type='error')
            return False
        log('Connected to broker on {} as {}'.format(self.broker, self.name))
        return True

    def mqttsend(self, topic: str, msg: str, retain=False):
        """Sends msg to topic. Logs activity and errors."""
        if not self.connected:
            self.connect()
        try:
            log(f'Sending {msg} to {topic}...')
            self.client.publish(topic, msg, retain=retain)
        except Exception as e:
            log('Error while sending: {}.'.format(e), log_type='error')
            return False
        print('Message sent.')
        log('Message sent.', log_type='debug')
        if self.clean_session:
            self.client.disconnect()
            self.connected = False
            print('Disconnected')
        return True

    def subscribe(self, topic):
        """Subscribes to the topic specifies. Logs activity and errors."""
        while not self.connected:
            if not self.connect():
                sleep(1)
        try:
            if topic not in self.subscriptions:
                self.client.subscribe(topic)
                self.subscriptions.append(topic)
                log('Subscribed: '+topic, log_type='debug')
            else:
                log('Already subscribed on '+topic, log_type='debug')
            return True
        except Exception as e:
            log('Could not subscribe', log_type='error')
            return False

    def check_for_messages(self):
        self.client.loop()

    def go_for_messages(self):
        self.client.loop_start()

    def wait_for_messages(self):
        self.client.loop_forever(retry_first_connection=True)

    def message_to_buffer(self, client, userdata, message):
        if message:
            log(f' Got {message.payload.decode()} in {message.topic}', log_type='debug')

            if self.external_handler:
                payload = parse_topic(message.topic)
                payload.append(message.payload.decode())
                self.external_handler.handle(payload)
            else:
                self.message_buffer.enqueue((message.topic, message.payload.decode()))

    def disconnect(self):
        self.client.disconnect()
        self.connected = False
        print('Disconnected')

    def on_disconnect(self, client, userdata, rc=0):
        log("Disconnected result code " + str(rc), log_type='debug')
        client.loop_stop()


class Dumb:

    def __init__(self):
        self.message_buffer = None

    def connect(self):
        pass
        #print('Dumb would not connect')

    def subscribe(self, topic):
        pass
        #print('Dumb would not subscribe')


#sender = Mqtt('syrabond_sender_' + str(uuid()), config='conf.json', clean_session=True)

def parse_topic(topic: str):
    """Split topic by / sign and return tuple of type, id and channel"""
    _type, _id, channel = None, None, None
    splited = topic.split('/')
    _type = topic.split('/')[1]
    _id = topic.split('/')[2]
    if len(splited) > 3:
        channel = '.'.join(topic.split('/')[3:])
    return [_type, _id, channel]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Wrong arguments")
        print("Usage: mqttsender.py <topic> <message>")
        sys.exit(-1)
    topic = sys.argv[1]
    msg = sys.argv[2]
    sender = Mqtt('Python_mqtt_sender')
    sender.mqttsend(topic, msg)
