**LAN Integrity Tester**
----
  A command-line program for Unix/Unix-like systems that estimates Local Area Network reliability via simple UDP exchanges over the network.

**Authors**  
  * Andrew Plank  
  * Trevor Hill
  
**Description**  
The LAN Integrity Tester tool is comprised of two components: The server and the client.  

  * Client  
    The Client can be used via the command-line by invoking the command `lic` (short for "LAN Integrity Client").   
    
    When invoked, the client will explore the network looking for compatible servers, select the first one it finds (assuming one exists), and together they will perform an integrity check. 

  * Server  
    The Server can be used via the command-line by invoking the command `lis` (short for "LAN Integrity Server").  
    
    The Server program is intended to run independently on another host somewhere on the Local Area Network (Although it is possibly a valid use case to test 'localhost' as well). A server instance must be active at the time the client is invoked in order for the client to produce reliability results. The server should be configured to run in the background of the given host machine. The host can be a shared machine (i.e. a standard frontend), or a dedicated host (i.e a raspberry pi). 

**Example**
```
$: lic
Running LAN Integrity check...
Searching for available servers...
Connected to host 192.168.2.231
Transmitting...
Round 1: 1 kbps
Round 2: 10 kbps
Round 3: 100 kbps
Round 4: 1 mpbs
Round 5: 10 mbps
Round 6: 100 mbps
Round 7: 250 mbps
Round 8: 500 mbps
Round 9: 750 mbps
Round 10: 1 gbps
Testing complete
Results:
Round  Rate       Lost     Mangled    Rating
  1 : 1 kbps       0%         0%       Pass
  2 : 10 kbps      0%         0%       Pass
  3 : 100 kbps     0%         0%       Pass
  4 : 1 mpbs       0%         1%     Acceptable
  5 : 10 mbps      0%         1%     Acceptable
  6 : 100 mbps     4%         0%       Pass
  7 : 250 mbps     12%        0%       Pass
  8 : 500 mbps     46%        3%     Acceptable
  9 : 750 mbps     87%        4%       Fail
 10 : 1 gbps       93%        7%       Fail
 $:
```

**Notes**
*  For the sake of simplicity, this tool ignores the UDP transfer layer overhead (roughly 8 bytes) and IP layer overhead (roughly 20 bytes) when testing at specified data rates. Transmission rates are explicitly in terms of payload size, NOT link utilization.

