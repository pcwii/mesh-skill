from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG
from mycroft.audio import wait_while_speaking
from mycroft.skills.context import adds_context, removes_context
from mycroft.api import DeviceApi

# import sys
from websocket import create_connection

# from time import sleep
import uuid
import string
import random
import json
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import re

__author__ = 'PCWii'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)

# clear any previously connected mqtt clients on first load
try:
    mqttc
    LOG.info('Client exist')
    mqttc.loop_stop()
    mqttc.disconnect()
    LOG.info('Stopped old client loop')
except NameError:
    mqttc = mqtt.Client()
    LOG.info('Client created')


# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"
class MeshSkill(MycroftSkill):

    # The constructor of the skill, which calls Mycroft Skill's constructor
    def __init__(self):
        super(MeshSkill, self).__init__(name="MeshSkill")
        # Initialize settings values
        self._is_setup = False
        self.notifier_bool = True
        self.deviceUUID = ''  # This is the unique ID based on the Mac of this unit
        self.targetDevice = ''  # This is the targed device_id obtained through mycroft dialog
        self.base_topic = ''
        self.MQTT_Enabled = ''
        self.MQTT_Retained = ''
        self.broker_address = ''
        self.broker_port = ''
        self.broker_uname = ''
        self.broker_pass = ''
        self.location_id = ''
        self.response_location = ''

    def on_connect(self, mqttc, obj, flags, rc):
        LOG.info("Connection Verified")
        LOG.info("This device location is: " + DeviceApi().get()["description"])
        mqtt_path = self.base_topic + "/RemoteDevices/" + str(self.location_id)
        qos = 0
        mqttc.subscribe(mqtt_path, qos)
        LOG.info('Mesh-Skill Subscribing to: ' + mqtt_path)

    def on_disconnect(self, mqttc, obj, flags, rc):
        self._is_setup = False
        LOG.info("MQTT has Dis-Connected")

    def on_message(self, mqttc, obj, msg):  # called when a new MQTT message is received
        # Sample Payload {"source":"basement", "message":"is dinner ready yet"}
        LOG.info('message received for location id: ' + str(self.location_id))
        LOG.info("This device location is: " + DeviceApi().get()["description"])
        try:
            mqtt_message = msg.payload.decode('utf-8')
            LOG.info(msg.topic + " " + str(msg.qos) + ", " + mqtt_message)
            new_message = json.loads(mqtt_message)
            if "command" in new_message:
                # example: {"source":"kitchen", "command":"what time is it"}
                LOG.info('Command Received! - ' + new_message["command"] + ', From: ' + new_message["source"])
                self.response_location = new_message["source"]
                self.send_message(new_message["command"])
            elif "message" in new_message:
                # example: {"source":"kitchen", "message":"is dinner ready yet"}
                self.response_location = ''
                LOG.info('Message Received! - ' + new_message["message"] + ', From: ' + new_message["source"])
                self.speak_dialog('location', data={"result": new_message["source"]}, expect_response=False)
                wait_while_speaking()
                self.speak_dialog('message', data={"result": new_message["message"]}, expect_response=False)
            elif "wakeup" in new_message:
                # example to remotely wakeup mycroft: {"source":"kitchen", "wakeup":true}
                if new_message["wakeup"]:
                    LOG.info('Remote Listen Received From: ' + new_message["source"])
                    LOG.info('Sending Wakeup Command to Messaagebus')
                    self.send_message('mycroft.mic.listen')
            else:
                LOG.info('Unable to decode the MQTT Message')
        except Exception as e:
            LOG.error('Error: {0}'.format(e))

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        self.load_data_files(dirname(__file__))
        #  Check and then monitor for credential changes
        #self.settings.set_changed_callback(self.on_websettings_changed)
        self.settings_change_callback = self.on_websettings_changed
        self.on_websettings_changed()
        self.deviceUUID = self.get_mac_address()
        self.add_event('recognizer_loop:utterance', self.handle_utterances)  # should be "utterances"
        self.add_event('speak', self.handle_speak)  # should be "utterance"
        mqttc.on_connect = self.on_connect
        mqttc.on_message = self.on_message
        mqttc.on_disconnect = self.on_disconnect
        if self._is_setup:
            self.mqtt_init()

    def clean_base_topic(self, basetopic):
        if basetopic[-1] == "/":
            basetopic = basetopic[0:-1]
        if basetopic[0] == "/":
            basetopic = basetopic[1:]
        return basetopic

    def on_websettings_changed(self):  # called when updating mycroft home page
        self._is_setup = False
        self.MQTT_Enabled = self.settings.get("MQTT_Enabled", False)  # used to enable / disable mqtt
        self.MQTT_Retained = self.settings.get("MQTT_Retained", False)  # used to enable / disable message retention
        self.broker_address = self.settings.get("broker_address", "127.0.0.1")
        raw_base_topic = self.settings.get("base_topic", "Mycroft")
        self.base_topic = self.clean_base_topic(raw_base_topic)
        self.broker_port = self.settings.get("broker_port", 1883)

        self.broker_uname = self.settings.get("broker_uname", "")
        self.broker_pass = self.settings.get("broker_pass", "")
        # self.location_id = self.settings.get("location_id", "basement")  # This is the device_id of this device
        this_location_id = str(DeviceApi().get()["description"])
        self.location_id = this_location_id.lower()
        LOG.info("This device location is: " + str(self.location_id))
        try:
            mqttc
            LOG.info('Client exist')
            mqttc.loop_stop()
            mqttc.disconnect()
            LOG.info('Stopped old client loop')
        except NameError:
            mqttc = mqtt.Client()
            LOG.info('Client re-created')
        LOG.info("Websettings Changed! " + self.broker_address + ", " + str(self.broker_port))
        self.mqtt_init()
        self._is_setup = True

    def mqtt_init(self):  # initializes the MQTT configuration and subscribes to its own topic
        if self.MQTT_Enabled:
            LOG.info('MQTT Is Enabled')
            try:
                LOG.info("Connecting to host: " + self.broker_address + ", on port: " + str(self.broker_port))
                if self.broker_uname and self.broker_pass:
                    LOG.info("Using MQTT Authentication")
                    mqttc.username_pw_set(username=self.broker_uname, password=self.broker_pass)
                mqttc.connect_async(self.broker_address, self.broker_port, 60)
                mqttc.loop_start()
                LOG.info("MQTT Loop Started Successfully")
                # LOG.info("This device location is: " + DeviceApi().get()["description"])
            except Exception as e:
                LOG.error('Error: {0}'.format(e))

    def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def get_mac_address(self):  #used to create a unique UUID for this device that
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        LOG.info("MQTT using UUID: " + mac)
        return mac

    def location_regex(self, message_str):
        return_list = []
        regex_string = r".*((to the|to)|(at the|at)) (?P<location>.*)"
        pri_regex = re.search(regex_string, message_str)
        if pri_regex:
            ret_location = pri_regex.group("location")
            # print(ret_location)
            return ret_location

    # utterance event used for notifications ***This is what the user requests***
    def handle_utterances(self, message):
        mqtt_path = self.base_topic + "/RemoteDevices/" + self.deviceUUID + "/request"
        # LOG.info(mqtt_path)
        voice_payload = str(message.data.get('utterances')[0])
        if self.notifier_bool:
            try:
                # LOG.info(voice_payload)
                self.send_MQTT(mqtt_path, voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    # mycroft speaking event used for notificatons ***This is what mycroft says***
    def handle_speak(self, message):
        mqtt_path = self.base_topic + "/RemoteDevices/" + self.deviceUUID + "/response"
        # LOG.info(mqtt_path)
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                self.send_MQTT(mqtt_path, voice_payload)
                LOG.info("Response Location Length: " + str(len(self.response_location)))
                if len(self.response_location) == 0:
                    self.response_location = ''
                else:
                    reply_payload = {
                        "source": str(self.location_id),
                        "message": voice_payload
                    }
                    reply_path = self.base_topic + "/RemoteDevices/" + self.response_location
                    self.response_location = ''
                    self.send_MQTT(reply_path, reply_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def send_MQTT(self, my_topic, my_message):  # Sends MQTT Message
        # LOG.info("This device location is: " + DeviceApi().get()["description"])
        if self.MQTT_Enabled and self._is_setup:
            LOG.info("MQTT: " + my_topic + ", " + json.dumps(my_message))
            # myID = self.id_generator()
            LOG.info("address: " + self.broker_address + ", Port: " + str(self.broker_port))
            publish.single(my_topic, json.dumps(my_message), hostname=self.broker_address, retain=self.MQTT_Retained)
        else:
            LOG.info("MQTT has been disabled in the websettings at https://home.mycroft.ai")

    def send_message(self, message):  # Sends the remote received commands to the messagebus
        LOG.info("Sending a command to the message bus: " + message)
        payload = json.dumps({
            "type": "recognizer_loop:utterance",
            "context": "",
            "data": {
                "utterances": [message]
            }
        })
        uri = 'ws://localhost:8181/core'
        ws = create_connection(uri)
        ws.send(payload)
        ws.close()

    # First step in the dialog is to receive the initial request to "send a message/command"
    # Todo Add .optionally("LocationRegex") to make the intent spoken language agnostic
    @intent_handler(IntentBuilder("SendMessageIntent").require("SendKeyword").require("MessageTypeKeyword")
                    .optionally("RemoteKeyword").build())
    def handle_send_message_intent(self, message):
        message_json = {}  # create json object
        message_json['source'] = str(self.location_id)
        # message_json = {'source': str(self.location_id)}
        msg_type = message.data.get("MessageTypeKeyword")
        voice_payload = str(message.data.get('utterance'))
        location_request = self.location_regex(voice_payload)
        if location_request is None:  # location was not in the utterance
            LOG.info("The user did not speak a location")
            # Have Mycroft request the location
            location_payload = self.get_response('request.location', data={"result": msg_type})
            if location_payload is None:
                LOG.info("Didn't receive a location string")
            else:
                words_spoken = len(location_payload.split())  # were more than one word(s) spoken
            if words_spoken > 1:
                location_request = self.location_regex(location_payload)
            else:
                location_request = location_payload
        else:  # location was in the utterance
            LOG.info("The user spoke the following location: " + location_request)
        self.targetDevice = location_request
        message_json[msg_type] = self.get_response('request.details', data={"result": msg_type})
        LOG.info("Preparing to Send a message to " + self.targetDevice)
        self.speak_dialog('sending.message', data={"message": msg_type, "location": self.targetDevice},
                          expect_response=False)
        mqtt_path = self.base_topic + "/RemoteDevices/" + str(self.targetDevice).lower()
        self.send_MQTT(mqtt_path, message_json)

    def stop(self):
        pass


# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return MeshSkill()
