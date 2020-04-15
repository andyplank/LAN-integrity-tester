#!/usr/bin/python

import socket
import sys
import time

PORT = 8080

if __name__ == "__main__":

    ## ARG CHECKING ##
    # if(len(sys.argv)!=2):
    #     print('Invalid args.\nTry ./server.py <PORT>')
    #     exit(1)
    # else:
    #     try:
    #         PORT = int(sys.argv[1])
    #     except ValueError:
    #         print('Invalid args.\nPort must be a number')
    #         exit(1)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('',PORT))
    lastMsgTime = False
    while True:
        data, address = s.recvfrom(1024)
        print(data)
        if lastMsgTime:
            elapsed = time.time() - lastMsgTime
            print(elapsed)
        lastMsgTime = time.time()
