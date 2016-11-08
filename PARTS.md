#Parts description
The HERA Part Number (hpn) is the alphanumeric primary key to track parts and connections.  Parts 
have ports that enable connections.  Port A is a skyward connection point and port B is further 
from the sky.

HERA Part Numbers are unique identifiers.

In concept, a part is something that can break — the one exception is that the station is viewed as 
a part in order to connect to a location.

Parts have an associated manufactures number (e.g. for antenna, it is the serial number).
Parts have a location.
'Z' is a reserved prefix for arbitrary hera part numbers we wish to track.
For now, all of the <int*> values correspond to the PAPER antenna number -- 
    ultimately, station/antenna hpn should be the same and rest will be serial numbers

Connections:  if there are equal connection points between ports A and B of a part, they connect 
through by changing A->B (as opposed to the other case where there is one to multiple).  If this
changes, we will define an internal port-to-port wiring.

#Station Part:  station
The station “part” comprises the following sub-arrays:
HH[<int>] - refers to the HERA-19 hex number (HH)
PH[<int>] - refers to the PAPER elements in a mirrored hex.  <int> corresponds to HH <int>
PI[<int>] - refers to the PAPER elements in the “imaging” configuration.
PP[A-G][<int>] - refers to the PAPER elements in the PAPER grid that are rotated 45deg
S[A-G][<int>] refers to the PAPER elements in the PAPER grid
There is a one-to-one correspondence to station_name and station_number (<int*>), which is the location 
integer used in e.g. MIRIAD.
Port A:  sky
Port B:  ground

#Antenna:  dish
The antenna part number, ultimately for HERA dishes it should agree with the station_number
A[<int*>]
Port A:  ground
Port B:  focus

#Feed:  feed
The feed part sits at the feed vertex:
FD[A-Z][<int*>]
        where [A-Z] represents a version letter and <int> a serial number
Port A:  feed input
Port B:  feed terminals

#Front-end:  frontend
The front-end plugs into the feed:
FE[A-Z][<int*>]
    where [A-Z] represents a version letter and <int> a serial number
Port A:  input
Port B:  N, E

#Feed cable:  cable_feed75
Cable between the feed and receiverator, consisting of a pair of coax
CBL[5,7]F[<int*>]
     where [5,7] refers to 50 or 75 ohms and <int> corresponds at least initially to the antenna number
Port A:  NA, EA
Port B:  NB, EB

#Receiver input cable:  cable_receiverin
Cable inside the receiverator from the bulkhead to the receiver
RI[1-8][A-B][1-8][N,E]
    where [1-8] corresponds to the receiverator
          [A-B] corresponds to the top or bottom set
          [1-8] corresponds to the place within the set
          [N,E] corresponds to top (E) or bottom (N)
Port A:  A
Port B:  B

#Receiver:  receiver
The receiver
RCVR[<int>]
    where <int> is a serial number
Port A:  NE, EA
Port B:  NB, EB

#Receiver output cable:  cable_receiverout
Cable inside the receiverator from the receiver to the bulkhead
RO[1-8][A-B][1-8][N,E]
    where values are per above
Port A:  A
Port B:  B

#Receiverator cable:  cable_receiverator
Cable from the receiverator to the container
CBLR[1-8][A-B][1-8][N,E]
    where values are per above
Port A:  A
Port B:  B

#Container cable:  cable_container
Cable in the container from the bulkhead plate to the f-engine
CBLC[1-6]R[1-8]C[1-6]
    where [1-6] is the plate
          [1-8] is the row on the plate
          [1-6] is the column on the plate
Port A:  A
Port B:  B

#F-engine ROACH-2 connector:  f_engine
R2[1-8][A-H][1-4]
    where [1-8] is the roach box
          [A-H][1-4] is the input connector
Port A:  Input
Port B:  Output
