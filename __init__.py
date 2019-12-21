from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG

from time import sleep
import string
import random
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

import re

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
        self.myKeywords = []
        # self.client = ''  # mqtt.Client()

        # Initialize settings values
        self.client = mqtt.Client(self.id_generator())
        self._is_setup = False
        self.notifier_bool = True

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        self.load_data_files(dirname(__file__))

        #  Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        self.on_websettings_changed()

        self.add_event('recognizer_loop:wakeword', self.handle_listen)  # should be "utterance"
        self.add_event('recognizer_loop:utterance', self.handle_utterances) # should be "utterances"
        self.add_event('speak', self.handle_speak)# should be "utterance"


    def on_websettings_changed(self):  # called when updating mycroft home page
        #if not self._is_setup:
        self.broker_address = self.settings.get("broker_address", "192.168.0.43")
        self.broker_port = self.settings.get("broker_port", 1883)
        self.plcOutTagName = self.settings.get("plc_out_tag_name", "StartRobot")
        self._is_setup = True
        LOG.info("Websettings Changed! " + self.broker_address + ", " + str(self.broker_port))

    def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    # utterance event used for notifications ***This is what the user says***
    def handle_utterances(self, message):
        voice_payload = str(message.data.get('utterances')[0])
        if self.notifier_bool:
            try:
                LOG.info(voice_payload)
                self.send_MQTT("Mycroft/Student", voice_payload)

            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    # mycroft speaking event used for notificatons ***This is what mycroft says***
    def handle_speak(self, message):
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                LOG.info(voice_payload)
                self.send_MQTT("Mycroft/AI", voice_payload)
                #self.card_conversation()
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def send_MQTT(self, myTopic, myMessage):
        if self.MQTT_Enabled:
            LOG.info("MQTT: " + myTopic + ", " + myMessage)
            myID = self.id_generator()
            #LOG.info("MyID: " + str(myID))
            #self.client = mqtt.Client(myID)
            #self.client.connect(self.broker_address, self.broker_port)  # connect to broker
            #self.client.publish(myTopic, myMessage)  # publish
            #self.client.disconnect()
            LOG.info("address: " + self.broker_address + ", Port: " + str(self.broker_port))
            publish.single(myTopic, myMessage, hostname=self.broker_address)
        else:
            LOG.info("MQTT has been disabled in the websettings at https://home.mycroft.ai")

    def stop(self):
        pass


# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return MeshSkill()
