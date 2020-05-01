**LAN Integrity Tester**
----
  A command-line server-client utility for Unix/Unix-like systems that estimates Local Area Network reliability via simple UDP exchanges over the network.

**Authors**  
  * Andrew Plank  
  * Trevor Hill
  
**Description**  
The LAN Integrity Tester tool is comprised of two components: The server and the client.  

  * Client  
    The Client can be used via the command-line by invoking the command `lic` (short for "LAN Integrity Client").   
    
    `lic` expects/supports the following arguments: `lic.py [-h] [-a [ADDRESS]] [-p [PORT]] [-l [LOSS]] [-rt] [-br] [-brp [BROAD_PORT] rounds rate`
    
    ```
    positional arguments:
      rounds            The number of tranmission rounds to be performed (number
                        of divisions of the transmission rate) (max 25)
      rate              The maximum rate of data transfer to be incrementally
                        tested up to in mbps (max 1gbps)
 
    optional arguments:
      -h, --help         show this help message and exit
      -a [ADDRESS]       The IP address of the desired server
      -p [PORT]          The port number of the desired server
      -l [LOSS]          An artificial amount of loss to be added.
      -rt                A flag to enable round trip mode.
      -br                A flag to disable UDP broadcast to find the server.
      -brp [BROAD_PORT]  The port number that the server will listen for
                        broadcasts on. Default is 4322
    ```

    * Example Usage:  
      * `lic.py 5 100` will invoke the client to search for servers active on the network, connect to one if found, and proceed to the testing procedure. `5` specifies that the maximum rate `100 (mpbs)` will be divided into 5 rounds, such that each round tests at a rate of `round * (rate / 5)`, or in this specific case, `round * (100 mbps / 5)`. In simplier terms, the network will be tested in increments of `20 mbps` such that rounds 1, 2, 3, 4, 5 tests at data rates of 20 mbps, 40mpbs, 60mbps, 80mbps, 100mbps, respectively. 
  
  * Server  
    The Server can be used via the command-line by invoking the command `lis` (short for "LAN Integrity Server").  
    
    `lis` expects/supports the following arguments: `lis.py [-h] [-p [TCP_PORT]] [-rt] [-br] [-brp [BROAD_PORT]]`
    ```
    optional arguments:
      -h, --help         show this help message and exit
      -p [TCP_PORT]      The desired TCP port for the server to bind to
      -rt                A flag to enable round trip mode.
      -br                A flag to disable UDP broadcast to find the server.
      -brp [BROAD_PORT]  The port number that the server will listen for
                        broadcasts on. Default is 4322
    ```

    * Example Usage:
      * `lis.py -rt` will invoke the server in its simpliest form (complete auto-configuration) with `round trip` (bidirectional testing) enabled. This configuration will utilize UDP broadcasting to automatically identify itself to `lic.py` calls searching for a server elsewhere on the LAN. 

**Examples**
```
$ python3 ./lic.py 5 100 -l 0.9
Broadcast mode enabled. Attempting to locate the server...
Server located at 192.168.1.188:62994
Establishing a connection to the test server...
Successfully established a connection to the test server.
Setting up testing environment...
Successfully established testing environmnet.
Beginning testing procedure...

Running round 1 of 5...
Current_rate is 20000000.0
packet_count is 271
sleep_time is 0.0036900369003690036
Round 1 complete
Running round 2 of 5...
Current_rate is 40000000.0
packet_count is 542
sleep_time is 0.0018450184501845018
Round 2 complete
Running round 3 of 5...
Current_rate is 60000000.0
packet_count is 813
sleep_time is 0.0012300123001230013
Round 3 complete
Running round 4 of 5...
Current_rate is 80000000.0
packet_count is 1085
sleep_time is 0.0009216589861751152
Round 4 complete
Running round 5 of 5...
Current_rate is 100000000.0
packet_count is 1356
sleep_time is 0.0007374631268436578
Round 5 complete


Results from server:
+---------+---------------+-----------+------------+---------------+----------+------------+
|   Round |   Rate (mbps) |   Packets |   Lost (%) |   Mangled (%) | Rating   |   Duration |
+=========+===============+===========+============+===============+==========+============+
|       1 |            20 |       271 |    93.3579 |             0 | fail     |    1.23643 |
+---------+---------------+-----------+------------+---------------+----------+------------+
|       2 |            40 |       542 |    91.1439 |             0 | fail     |    1.33068 |
+---------+---------------+-----------+------------+---------------+----------+------------+
|       3 |            60 |       813 |    90.4059 |             0 | fail     |    1.37516 |
+---------+---------------+-----------+------------+---------------+----------+------------+
|       4 |            80 |      1085 |    89.4931 |             0 | fail     |    1.42259 |
+---------+---------------+-----------+------------+---------------+----------+------------+
|       5 |           100 |      1356 |    89.0855 |             0 | fail     |    1.4835  |
+---------+---------------+-----------+------------+---------------+----------+------------+
```

**Notes**
*  For the sake of simplicity, this tool ignores the UDP transfer layer overhead (roughly 8 bytes) and IP layer overhead (roughly 20+ bytes) when testing at specified data rates. Transmission rates are explicitly in terms of payload size, NOT link utilization.
*  As of now, due to OS differences and calculation simplicity, specified bandwidth rates are not accurate, and should not be assumed to be. For now, the tool serves as a functional proof of concept, but for now, payload sizes are static in order to satisfy the varying limits set in place by various OSes (ex. MacOS caps the maximum UDP payload size to 9216 by default, and we do not want users to need to modify these defaults.)