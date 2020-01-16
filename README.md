# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/broadcast-tower.svg' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Mesh
send MQTT messages and commands between multiple mycroft.ai devices.

## About
A flock of Seagulls, a pride of Lions, a swarm of Bees, and a "mesh of Mycrofts".

This skill utilizes the lightweight MQTT messaging protocol to connect a group ("mesh") of Mycroft units together. The skill has the ability to send messages (intercom) and commands (messagebus) to one or more remote Mycroft units.
1. Each Mycroft unit has the ability to publish both Mycroft requests and responses to the the MQTT broker.
The MQTT Topics for this communication is...
    * ```<base_topic>/RemoteDevices/deviceUUID/request```
    * ```<base_topic>/RemoteDevices/deviceUUID/response```
2. The deviceUUID is a unique ID created from the MAC of the sending Mycroft unit.
*This is intended to be a general MQTT broadcast and can be subscribed to by any MQTT client (ie. Home Assistant?).
3. Each Mycroft unit has it's own Device Name (location_id) that can be set in the web interface.
4. The Mycroft unit will automatically subscribe to all messages sent to it's own Device Name (location_id).
    * ```<base_topic>/RemoteDevices/<location_id>```
    * The <location_id> is automatically obtained from the Mycroft Device Settings web page...
    ![location_id](/images/location_id.png)
    * location id's are automatically converted to lowercase to avoid confusion
    
5. When a message is sent from any Mycroft unit, the message will be published to "Mycroft/RemoteDevices/location_id".
6. The destination location_id is specified in the skill dialog.
7. The message payload will contain the following Json...
    * ```{"source":"<source_location_id>", "message":"is dinner ready yet"}```

## Examples
* "Send a remote message"
* "Send a remote command"

## Credits
pcwii

## Category
**IoT**

## Tags
#mesh
#remote
#connect
#control
#MQTT
#HA
#Homeassistant

## Overview
![Overview](/images/mesh-skill.png)

## Conversational Context
- Example 1 (from basement to kitchen)
```
hey mycroft...
    send a message...
where would you like to send the message?...
    kitchen...
what would you like the message to be?...
    Is dinner ready yet?
I am preparing to send a, message, to the, kitchen, device.
mycroft publishes...
"<base_topic>/RemoteDevices/kitchen/{"source":"basement", "message":"is dinner ready yet"}
```
- Example 2 (from kitchen to basement)
```
hey mycroft...
    send a command...
where would you like to send the command?...
    basement...
what would you like the command to be?...
    set a timer for 5 minutes?
Sending command, to the basement.
mycroft publishes...
"<base_topic>/RemoteDevices/basement/{"source":"kitchen", "command":"set a timer for 5 minutes"}
```
- Example 3 (specify location in original command)
```
hey mycroft...
    send a command to the basement...
what would you like the command to be?...
    set a timer for 5 minutes?
Sending command, to the basement.
mycroft publishes...
"<base_topic>/RemoteDevices/basement/{"source":"kitchen", "command":"set a timer for 5 minutes"}
```
- Example 4 (polite request)
```
hey mycroft...
    send a command...
where would you like to send the command?...
    to the basement...
what would you like the command to be?...
    set a timer for 5 minutes?
Sending command, to the basement.
mycroft publishes...
"<base_topic>/RemoteDevices/basement/{"source":"kitchen", "command":"set a timer for 5 minutes"}
```
## Installation Notes
- ensure you have a working MQTT Broker. [how to install mqtt broker.](https://github.com/pcwii/mesh-skill/blob/master/broker_install.md)
- SSH and run: msm install https://github.com/pcwii/mesh-skill.git
- Configure home.mycroft.ai
    * Ensure MQTT is enabled.
    * Create a custom base topic name <base_topic>. This can be any MQTT formatted topic.
        * <base_topic> = Mycroft, <base_topic> = Mycroft/Cottage, <base_topic> = abcdef/myhome,   
    * Set IP Address of your broker
    * Set the websocket Port of your broker.
    * The <location_id> is automatically obtained from the Device websettings "Placement".
    * **This skill must be installed, and configured for each unit in your "mesh"**
    * **MQTT paths are case sensitive**

## Requirements
- [paho-mqtt](https://pypi.org/project/paho-mqtt/).
- [Mycroft](https://docs.mycroft.ai/installing.and.running/installation).
- [Websockets](https://pypi.org/project/websockets/)

## Warnings!!
- It is not recommended to use a public MQTT broker at this time as this could expose your commands to other Mycroft Units, or other devices subscribing to your topic.
    * Ensure you use a unique <base_topic> for your group (mesh) of mycroft units.
    * You may segment your groups (meshes) by using different <base_topic> for each group (mesh). 
## Todo
- ~~Connect subscribed "commands" to message bus (20191231)~~
- Investigate enabling remote mycroft to reply to messages (20191231)
    * ```{"source":"basement", "message":"is dinner ready yet", "reply": True}```
- ~~Provide a customization for Topic Names to increase security.(20191231)~~
- Add prompting on remote receiving device before playing messages.(20191231)
    * Not sure this has value if room is unoccupied.
- Add prompting on remote receiving device before executing commands messages.(20191231)
    * Not sure this has value if room is unoccupied.  
- ~~Redirect remote responses to the commanding mycroft unit (20200102)~~
- Autodiscovery???(20191231)
- ~~Add Authentication (20200109)~~
- ~~Remove Location ID websetting and retrieve from device configuration web page (20200113)~~
- ~~Add ability to speak location in the initial request(20200116)~~

