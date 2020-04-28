#!/usr/bin/python

import argparse
import json
import socket
import sys
import time
import threading
import random

def main():

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('-p', dest='port', type=int, nargs='?', help='The desired TCP port for the server to bind to')
    args = parser.parse_args()

    # Check argument validity
    if args.port:
        if args.port < 0 or args.port > 65535:
            print("Error: Argument 'port' must be in the range 0 < x <= 65535")
            exit(1)
        if args.port < 1024:
            print("Warning: Argument 'port' is a well-defined port. This may require superuser permissions")
        elif args.port < 49151:
            print("Warning: Argument 'port' is a registered port. Port collision is possible")

    # Extract parsed arguments
    if (args.port):
        tcp_port = args.port
    else:
        tcp_port = 62994

    # Establish server at specified port number and await a connection
    print(f"Establishing listening server on port {tcp_port}...")
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('localhost', tcp_port))
    tcp_socket.listen(1)

    # Serve indefinitely
    while True:
        tcp_conn, tcp_addr = tcp_socket.accept()

        # Service new connection
        print(f"Connection established by address {tcp_addr}")
        TCP_Connection_Handler(tcp_conn)

# Handles TCP connections for handling active tests.
# Is NOT intended to be threaded
def TCP_Connection_Handler(tcp_conn):
    # Await and decode connection synchronize request in JSON
    data = bytearray()
    byte = tcp_conn.recv(1)
    while byte != '':
        if b'\n' == byte:
            break
        data += byte
        byte = tcp_conn.recv(1)

    message = json.loads(data.decode('utf-8'))

    if 'status' not in message or message['status'] != 'synchronize':
        print("Connection did not properly synchronize")
        return

    # Bind UDP socket to a OS-specified port number
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('localhost', 0))

    # Send OS-allocated UDP port number to client as JSON
    response = {
        'status': 'synchronize-ack',
        'udp_port': udp_socket.getsockname()[1]
    }
    tcp_conn.send(json.dumps(response).encode('utf-8') + b'\n')

    # Global round result storage
    results = []

    # Handle each transmission round until client terminates test
    while True:
        # Await and decode round configuration JSON
        data = bytearray()
        byte = tcp_conn.recv(1)
        while byte != '':
            if b'\n' == byte:
                break
            data += byte
            byte = tcp_conn.recv(1)

        round_config = json.loads(data.decode('utf-8'))

        # If testing is complete, compute results, return to sender, and terminate connection
        if (round_config['status'] == 'test_complete'):
            print("Test complete... Returning")
            tcp_conn.send(json.dumps(results).encode('utf-8') + b'\n')
            tcp_conn.close()
            return

        # Getting artificial loss value from config
        if round_config['loss'] > 1 or round_config['loss'] < 0:
            print("Error: Argument 'loss' must be in the range 0 <= x <= 1")
            tcp_conn.send(json.dumps("Error: Argument 'loss' must be in the range 0 <= x <= 1").encode('utf-8') + b'\n')
            tcp_conn.close()
            return
        loss = round_config['loss']

        # Testing has proceeded to the next round. Spawn handler and signal ready
        stop_signal = False
        payload_map = dict()
        listener_thread = threading.Thread(target=UDP_Listener, args=(udp_socket, payload_map, loss, lambda: stop_signal,))
        listener_thread.start()

        tcp_conn.send(json.dumps({'status': 'ready'}).encode('utf-8') + b'\n')

        # Await round completion JSON from client
        data = bytearray()
        byte = tcp_conn.recv(1)
        while byte != '':
            if b'\n' == byte:
                break
            data += byte
            byte = tcp_conn.recv(1)

        # Signal UDP listening thread to terminate and then await it
        stop_signal = True
        listener_thread.join()

        # Compute round results
        bytes_received = 0
        # for x in range(255):
        # bytes_received = bytes_received + payload_map[x]
        for key in payload_map:
            bytes_received = bytes_received + payload_map[key]

        lost_percent = (round_config['byte_count'] - bytes_received) / round_config['byte_count'] * 100
        rating = 'pass'

        if lost_percent > 1:
            rating = 'acceptable'
        if lost_percent > 7:
            rating = 'fail'

        results.append({
            'round': round_config['round'],
            'rate': round_config['rate'],
            'lost': lost_percent,
            'rating': rating
        })

        print(results)
        # Signal client that server is ready for the next round
        tcp_conn.send(json.dumps({'status': 'ready'}).encode('utf-8') + b'\n')

# Handles UDP listening on a separate thread so that the TCP connection can be monitored by main thread for status updates
# Param: udp_socket: The udp socket to be monitored
# Param: payload_map: The key-value dictionary, used such that payload_map[payload]++ to count payload instances
# Param: loss: A float value that specifies the amount of articial loss to be inserted into the analysis
# Param: signal: A boolean that signifies whether the thread should terminate after a period of no new packets
def UDP_Listener(udp_socket, payload_map, loss, signal):
    while True:
        udp_socket.settimeout(1)
        try:
            udp_msg, udp_addr = udp_socket.recvfrom(1)
            if(random.random() > loss):
                if int.from_bytes(udp_msg, 'little') in payload_map:
                    payload_map[int.from_bytes(udp_msg, 'little')] = payload_map[int.from_bytes(udp_msg, 'little')] + 1
                else:
                    payload_map[int.from_bytes(udp_msg, 'little')] = 1
        except socket.timeout:
            if signal():
                return

if __name__ == "__main__":
    main()