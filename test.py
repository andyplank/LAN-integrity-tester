#!/usr/bin/python

import socket
import sys
import time

PORT = 8080

if __name__ == "__main__":

    ## ARG CHECKING ##
    # if(len(sys.argv)!=2):
    #     print('Invalid args.\nTry ./test.py <PORT>')
    #     exit(1)
    # else:
    #     try:
    #         PORT = int(sys.argv[1])
    #     except ValueError:
    #         print('Invalid args.\nPort must be a number')
    #         exit(1)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = b'Hello World'
    addr = ("127.0.0.1", PORT)

    for i in range(10):
        s.sendto(message, addr)
        time.sleep(1)
