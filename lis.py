#!/usr/bin/python

import argparse
import socket
import sys
import time

if __name__ == "__main__":

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('-p', dest='port', type=int, nargs='?', help='The desired TCP port for the server to bind to')
    args = parser.parse_args()

    # Extract parsed arguments
    if (args.port):
        tcp_port = args.port
    else:
        tcp_port = 69420

    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # s.bind(('',PORT))
    # lastMsgTime = False
    # while True:
    #     data, address = s.recvfrom(1024)
    #     print(data)
    #     if lastMsgTime:
    #         elapsed = time.time() - lastMsgTime
    #         print(elapsed)
    #     lastMsgTime = time.time()
