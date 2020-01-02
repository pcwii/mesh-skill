from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG
from mycroft.audio import wait_while_speaking

# import sys
from websocket import create_connection

# from time import sleep
import uuid
import string
import random
import json
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
# import re

__author__ = 'PCWii'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)


# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"
class MeshSkill(MycroftSkill):

    # The constructor of the skill, which calls Mycroft Skill's constructor
    def __init__(self):
        super(MeshSkill, self).__init__(name="MeshSkill")
        # Initialize settings values
        self.client = mqtt.Client(self.id_generator())
        self._is_setup = False
        self.notifier_bool = True
        self.deviceUUID = ''  # This is the unique ID based on the Mac of this unit
        self.targetDevice = ''  # This is the targed device_id obtained through mycroft dialog
        self.base_topic = ''
        self.MQTT_Enabled = ''
        self.broker_address = ''
        self.broker_port = ''
        self.location_id = ''

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        self.load_data_files(dirname(__file__))
        #  Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        self.on_websettings_changed()
        self.deviceUUID = self.get_mac_address()
        #self.add_event('recognizer_loop:wakeword', self.handle_listen)  # should be "utterance"
        self.add_event('recognizer_loop:utterance', self.handle_utterances)  # should be "utterances"
        self.add_event('speak', self.handle_speak)  # should be "utterance"

    def on_websettings_changed(self):  # called when updating mycroft home page
        self.MQTT_Enabled = self.settings.get("MQTT_Enabled", False)  # used to enable / disable mqtt
        self.broker_address = self.settings.get("broker_address", "127.0.0.1")
        self.base_topic = self.settings.get("base_topic", "Mycroft")
        self.broker_port = self.settings.get("broker_port", 1883)
        self.location_id = self.settings.get("location_id", "basement")  # This is the device_id of this device
        self._is_setup = True
        LOG.info("Websettings Changed! " + self.broker_address + ", " + str(self.broker_port))
        self.mqtt_init()

    def mqtt_init(self):  # initializes the MQTT configuration and subscribes to its own topic
        if self.MQTT_Enabled:
            LOG.info('MQTT Is Enabled')
            mqtt_path = self.base_topic + "/RemoteDevices/" + self.location_id
            self.client.on_message = self.on_message
            self.client.connect(self.broker_address, self.broker_port, 60)
            qos = 0
            self.client.subscribe(mqtt_path, qos)
            LOG.info('Mesh-Skill Subscribing to: ' + mqtt_path)
            self.client.loop_start()

    def on_message(self, client, obj, msg):  # called when a new MQTT message is received
        LOG.info('message received for location id: ' + self.location_id)
        LOG.info(msg.payload)
        mqtt_message = str(msg.payload)[2:-1]
        new_message = json.loads(mqtt_message)
        LOG.info(msg.topic + " " + str(msg.qos) + ", " + mqtt_message)
        if "command" in new_message:
            LOG.info('Command Received! - ' + new_message["command"])
            self.send_message(new_message["command"])
        elif "message" in new_message:
            LOG.info('Message Received! - ' + new_message["message"])
            self.speak_dialog('location.dialog', data={"location": new_message["source"]}, expect_response=False)
            wait_while_speaking()
            self.speak_dialog('message.dialog', data={"message": new_message["message"]}, expect_response=False)

    def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def get_mac_address(self):  #used to create a unique UUID for this device that
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        LOG.info("MQTT using UUID: " + mac)
        return mac

    # utterance event used for notifications ***This is what the user requests***
    def handle_utterances(self, message):
        mqtt_path = self.base_topic + "/RemoteDevices/" + self.deviceUUID + "/request"
        LOG.info(mqtt_path)
        voice_payload = str(message.data.get('utterances')[0])
        if self.notifier_bool:
            try:
                LOG.info(voice_payload)
                self.send_MQTT(mqtt_path, voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    # mycroft speaking event used for notificatons ***This is what mycroft says***
    def handle_speak(self, message):
        mqtt_path = self.base_topic + "/RemoteDevices/" + self.deviceUUID + "/response"
        LOG.info(mqtt_path)
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                LOG.info(voice_payload)
                self.send_MQTT(mqtt_path, voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def send_MQTT(self, my_topic, my_message):  # Sends MQTT Message
        if self.MQTT_Enabled:
            LOG.info("MQTT: " + my_topic + ", " + my_message)
            # myID = self.id_generator()
            LOG.info("address: " + self.broker_address + ", Port: " + str(self.broker_port))
            publish.single(my_topic, my_message, hostname=self.broker_address)
        else:
            LOG.info("MQTT has been disabled in the websettings at https://home.mycroft.ai")

    def send_message(self, message):  # Sends the remote received commands to the messagebus
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
    @intent_handler(IntentBuilder("SendMessageIntent").require("SendKeyword").require("RemoteKeyword").
                    one_of("MessageKeyword", "CommandKeyword").build())
    def handle_send_message_intent(self, message):
        self.set_context('GetLocationContextKeyword', 'GetLocationContext')
        if "MessageKeyword" in message.data:
            self.set_context('MessageKeyword', 'message')
        if "CommandKeyword" in message.data:
            self.set_context('CommandKeyword', 'command')
        self.speak_dialog('request.location.dialog', data={"result": message.data}, expect_response=True)

    # Second step in the dialog is to request the location to send the message/command
    @intent_handler(IntentBuilder("GetLocationIntent").require("GetLocationContextKeyword").
                    one_of("MessageKeyword", "CommandKeyword").build())
    def handle_get_location_intent(self, message):
        self.set_context('GetLocationContextKeyword', '')
        self.set_context('GetDetailsContextKeyword', 'GetDetailsKeyword')
        self.targetDevice = str(message.utterance_remainder())
        if "MessageKeyword" in message.data:
            self.set_context('MessageKeyword', 'message')
        if "CommandKeyword" in message.data:
            self.set_context('CommandKeyword', 'command')
        self.speak_dialog('request.details.dialog', data={"result": message.data}, expect_response=True)

    # Third step is to combine everything
    @intent_handler(IntentBuilder("GetDetailsIntent").require("GetDetailsContextKeyword").
                    one_of("MessageKeyword", "CommandKeyword").build())
    def handle_get_details_intent(self, message):
        message_json = {}  # create json object
        self.set_context('GetLocationContextKeyword', '')
        self.set_context('GetDetailsContextKeyword', '')
        message_json['source'] = self.location_id
        if "MessageKeyword" in message.data:
            LOG.info("Preparing to Send a message to " + self.targetDevice)
            message_json['message'] = str(message.utterance_remainder())
        if "CommandKeyword" in message.data:
            LOG.info("Preparing to Send a command to " + self.targetDevice)
            message_json['command'] = str(message.utterance_remainder())
        LOG.info("Sending the following : " + str(message_json))
        mqtt_path = self.base_topic + "/RemoteDevices/" + self.targetDevice
        self.send_MQTT(mqtt_path, message_json)

    def stop(self):
        pass


# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return MeshSkill()
