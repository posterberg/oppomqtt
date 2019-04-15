#!/usr/bin/env python
from socket import SO_REUSEADDR, SOCK_STREAM, error, socket, SOL_SOCKET, AF_INET
from threading import Thread
import paho.mqtt.client as mqtt

from oppomessages import OPPOMSG

###   CONFIGURATION   ####################################################################################################

OPPO_HOST  = 'oppohost'             # IP address or hostname of the Oppo player
OPPO_PORT  = 23                     # Port to connect to, normally 25

MQTT_HOST  = 'mqtthost'             # IP address or hostname of the MQTT server
MQTT_PORT  = 1883                   # Port to connect to, normally 1883
MQTT_USER  = 'mqttuser'             # Username for MQTT connection, set to '' for no authentication
MQTT_PASS  = 'supersecretpassword'  # Password for MQTT connection
MQTT_TOPIC = '/multimedia/oppo/cmd' # Topic to subscribe to for sending commands to oppo and receiving responses
MQTT_BASE  = '/multimedia/oppo/'    # Base topic to use for sending status update from oppo

##########################################################################################################################

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    mqttc.subscribe(MQTT_TOPIC)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))

class Client:
    def __init__(self, host, port):
        self.s = socket(AF_INET, SOCK_STREAM)
        self.host = host
        self.port = port

    def sendmqtt(self, code, msg):
        mqttc.publish(MQTT_BASE + code, '{\'' + msg + '\':\'' + msg + '\'}', retain=True)

    def sendoppomqtt(self, code, msg):
        mqttc.publish(MQTT_BASE + code, '{\'' + msg + '\':\'' + OPPOMSG[code][msg] + '\'}', retain=True)

    def senddirectmqtt(self, msg):
        mqttc.publish(MQTT_TOPIC, msg)

    def clearoppostatus(self):
        self.sendmqtt('UPL', '')
        self.sendmqtt('UPL', '')
        self.sendmqtt('UVL', '')
        self.sendmqtt('UDT', '')
        self.sendmqtt('UAT', '')
        self.sendmqtt('UST', '')
        self.sendmqtt('UIS', '')
        self.sendmqtt('U3D', '')
        self.sendmqtt('UAR', '')
        self.sendmqtt('UTC', '')
        self.sendmqtt('UVO', '')
        self.sendmqtt('USB', '')

    def getmessage(self, data):
        code, msg = data.split(' ', 1)
        if code[0] == '@':
            code = code[1:]
            msg = msg.rstrip()

            # Check if not debug response
            if code == 'OK' or code == 'ER' or code == 'QC1' or code == 'QC2':
                # Pass thru response to MQTT_TOPIC
                self.senddirectmqtt(code + ' ' + msg)
            else:
                # Try to parse debug response
                if code in OPPOMSG:
                    if OPPOMSG[code] != None:
                        if msg in OPPOMSG[code]:
                            # Send json parsed response
                            self.sendoppomqtt(code, msg)

                            # Clear all retained statuses if turned off
                            if code == 'UPW' and code == '0':
                                self.clearoppostatus()
                        else:
                            if code == 'UVO':
                                msgs = msg.split(' ')
                                if len(msgs) == 2:
                                    source = ''
                                    output = ''
                                    if msgs[0] in OPPOMSG[code]:
                                        source = OPPOMSG[code][msgs[0]]
                                    if msgs[1] in OPPOMSG[code]:
                                        output = OPPOMSG[code][msgs[1]]

                                    publish = '{\'' + msg + '\':\'' + 'Source: ' + source + ' - Output: ' + output + '\'}'
                                    mqttc.publish(MQTT_BASE + code, publish, retain=False)
                    else:
                        if code == 'UTC':
                            msgs = msg.split(' ')
                            if len(msgs) == 4:
                                title = msgs[0]
                                chpt = msgs[1]
                                tc = msgs[2]
                                time = msgs[3]

                                if tc == 'E':
                                    tctext = 'Total Remaining time'
                                elif tc == 'T':
                                    tctext = 'Title Elapsed time'
                                elif tc == 'X':
                                    tctext = 'Title Remaining time'
                                elif tc == 'C':
                                    tctext = 'Chapter/track Elapsed time'
                                elif tc == 'K':
                                    tctext = 'Chapter/track Remaining time'
                                else:
                                    tctext = 'Unknown Time'

                                publish = '{\'' + msg + '\':\'' + 'Title: ' + title + ' - Chapter: ' + chpt + ' - ' + tctext + ': ' + time + '\'}'
                                mqttc.publish(MQTT_BASE + code, publish, retain=False)
                else:
                    # Send json unparsed response
                    self.sendmqtt(code, msg)

            return msg

        else:
            return False

    def run(self):
        try:
            # Timeout if the no connection can be made in 5 seconds
            self.s.settimeout(5)
            # Allow socket address reuse
            self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            # Connect to the host over the given port
            self.s.connect((self.host, self.port))

            # No time out, blocking
            self.s.settimeout(None)

            # Initiate Verbose Mode 3
            self.s.send("#SVM 3".encode())

            while True:
                # Wait to receive data back from server
                data = self.s.recv(1024).decode('utf-8').rstrip()

                # Handle multiple responses sent back from player split by \r
                datas = data.split('\r')
                for data in datas:
                    # Send raw message to MQTT_BASE/raw
                    mqttc.publish(MQTT_BASE + 'raw', data, retain=False)
                    # Parse message
                    message = self.getmessage(str(data))

            # CLOSE THE SOCKET
            self.s.close()

        # If something went wrong, notify the user
        except error as e:
            print("ERROR: ", str(e))

def worker():
    # Fork a worker process for handling incoming messages from player
    new_client = Client(OPPO_HOST, OPPO_PORT)
    new_client.run()

# Create a mqtt client object
mqttc = mqtt.Client()
mqttc.on_connect = on_connect
mqttc.on_message = on_message

# Set username and password if enabled
if MQTT_USER != '':
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)

# Connect to mqtt server
mqttc.connect(MQTT_HOST, MQTT_PORT, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
mqttc.loop_start()

t = Thread(target=worker)
t.daemon = True
t.run()

