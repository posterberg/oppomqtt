# oppomqtt
An Oppo UDP203/205 mqtt interface

This interface can be used to read current status from an Oppo UDP203 or UDP205 player.

The interface will connect to the configured IP address/hostname of an Oppo player and pass on it's status to an mqtt server.

All messages will be sent to the mqtt server both as the raw message, and in parsed format.

Parsed messages will be sent to it's respective mqtt topic retained, retained statuses will automatically be cleared if the player is switched off.

Setup connection information, passwords, and a base mqtt topic in the oppomqtt.py file. The location for each setting should be easy to spot.

Detailed information about statuses and the raw format can be found here, http://download.oppodigital.com/UDP203/OPPO_UDP-20X_RS-232_and_IP_Control_Protocol.pdf.

The player needs to be setup to not use power savings to allow that the service can keep its connection when the player is turned off.

The service will automatically enable verbose mode 3 on the player upon successful connect, described on page 18 in the referenced pdf.

Statuses will be sent to the following mqtt topics:

BASE = configured base topic
* BASE/raw - Raw messages as detailed in the referenced pdf
* BASE/UPW - Power status
* BASE/UPL - Playback status
* BASE/UVL - Volume level
* BASE/UDT - Disc type
* BASE/UAT - Audio type
* BASE/UST - Subtitle type
* BASE/UIS - Input source
* BASE/U3D - 3D status
* BASE/UAR - Aspect ratio status
* BASE/UTC - Time code
* BASE/UVO - Video resolution
