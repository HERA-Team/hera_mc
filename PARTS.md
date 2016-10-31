#Parts description

The HERA Part Number (hpn) is the alphanumeric primary key to track parts and connections.  Parts have ports that enable connections.  Port A is a skyward connection point and port B is further from the sky.

HERA Part Numbers are unique identifiers.

In concept, a part is something that can break — the one exception is that the station is viewed as a part in order to connect to a location.

Parts have an associated manufactures number (e.g. for antenna, it is the serial number).
Parts have a location.
'Z' is a reserved prefix for arbitrary hera part numbers we wish to track.

#Station Part
The station “part” comprises the following sub-arrays:
[<int>] - refers to the HERA-19 hex number (HH)
PH[<int>] - refers to the PAPER elements in a mirrored hex.  <int> corresponds to HH <int>
PI[<int>] - refers to the PAPER elements in the “imaging” configuration.
PP[A-G][<int>] - refers to the PAPER elements in the PAPER grid that are rotated 45deg
S[A-G][<int>] refers to the PAPER elements in the PAPER grid
There is a one-to-one correspondence to station_name and station_number, which is the location integer used in e.g. MIRIAD.
Port A is at the sky
Port B is at the ground

#Antenna
The antenna part number format is
A[<int>]
Port A is at the ground
Port B is at the feed

#Feed
The feed part sits at the feed vertex and the format is
FD[A-Z][<int>]
Currently we are version A.
Port A is at the antenna.
Port B is at the front-end

#Front-end
FE[<int>]
Port A is at the feed.
Port B is at the feed cable.

#Feed cable
CBLF[<int>]
Port A is at the front-end
Port B is at the receiverator input connector

#Receiver input cable
RI[1-8][A-B][1-8][N,E]
Port A is at the feed cable
Port B is at the receiver

#Receiver
RCVR[<int>]
Port A is at the receiver input cable
Port B is at the receiver output cable

#Receiver output cable
RI[1-8][A-B][1-8][N,E]
Port A is at the receiver
Port B is at the receiverator cable

#Receiverator cable
CBLR[1-8][A-B][1-8][N,E]
Port A is at the receiver output cable
Port B is at the container cable

#Container cable
CBLC[1-6]R[1-8]C[1-6]
Port A is at the receiverator cable
Port B is at the F-engine (ROACH-2)

#F-engine ROACH-2
R2[1-8][A-H[1-4]
Port A is at the container cable
Port B is at the switch cable
