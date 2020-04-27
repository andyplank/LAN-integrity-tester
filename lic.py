#!/usr/bin/python

import argparse
import socket
import sys
import time

if __name__ == "__main__":

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('Rounds', type=int, help='The number of tranmission rounds to be performed (number of divisions of the transmission rate)')
    parser.add_argument('Rate', type=int, help='The maximum rate of data transfer to be incrementally tested up to')
    parser.add_argument('-a', dest='address', type=int, nargs='?', help='The IP address of the desired server')
    parser.add_argument('-p', dest='port', type=int, nargs='?', help='The port number of the desired server')
    args = parser.parse_args()
    
    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # message = b'Hello World'
    # addr = ("127.0.0.1", PORT)

    # for i in range(10):
    #     s.sendto(message, addr)
    #     time.sleep(1)
