import json

import paho.mqtt.client as PahoMQTT
service_name = "vase_control"


class MyMQTT:
    def __init__(self, clientID, broker, port, notifier):
        self.broker = broker
        self.port = port
        self.notifier = notifier
        self.clientID = clientID
        self._topic = ""
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(PahoMQTT.CallbackAPIVersion.VERSION1, clientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        #print("Connected to %s with result code: %d" % (self.broker, rc))
        #log_to_loki("info", f"connected to {self.broker}", service_name=service_name, service_name=service_name, user_id=user_id, request_id=request_id)
        pass
    
    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        #log_to_loki("info", f"message received from topic {self.topic}", service_name=service_name, service_name=service_name, user_id=user_id, request_id=request_id)
        self.notifier.notify(msg.topic, msg.payload)

    def myPublish(self, topic, msg):
        # publish a message with a certain topic
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)
        #print(f"message published on topic: {topic}, {json.dumps(msg)}")
        #log_to_loki("info", f"message published to topic {self.topic}", service_name=service_name, service_name=service_name, user_id=user_id, request_id=request_id)

    def mySubscribe(self, topic):
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        self._topic = topic
        #log_to_loki("info", f"subscribed to {self.broker}", service_name=service_name, service_name=service_name, user_id=user_id, request_id=request_id)

        #print("subscribed to %s" % (topic))

    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def unsubscribe(self):
        if (self._isSubscriber):
            #log_to_loki("info", f"unsubscribed from {self._topic}", service_name=service_name, service_name=service_name, user_id=user_id, request_id=request_id)
            self._paho_mqtt.unsubscribe(self._topic)

    def stop(self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic)

        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
