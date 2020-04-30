#!/usr/bin/python3

import argparse
import json
import socket
import sys
import time
import threading
import random

def main():

    # Default port to listen for broadcasts
    broad_port = 4322
    brp_help = f'The port number that the server will listen for broadcasts on. Default is {broad_port}'

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('-p', dest='tcp_port', type=int, nargs='?', help='The desired TCP port for the server to bind to')
    parser.add_argument('-rt', action='store_true', help='A flag to enable round trip mode.')
    parser.add_argument('-br', action='store_false', help='A flag to disable UDP broadcast to find the server.')    
    parser.add_argument('-brp', dest='broad_port', type=int, nargs='?', help=brp_help)
    args = parser.parse_args()

    # Check TCP port argument validity
    if args.tcp_port:
        if args.tcp_port < 0 or args.tcp_port > 65535:
            print("Error: Argument 'port' must be in the range 0 < x <= 65535")
            exit(1)
        if args.tcp_port < 1024:
            print("Warning: Argument 'port' is a well-defined port. This may require superuser permissions")
        elif args.tcp_port < 49151:
            print("Warning: Argument 'port' is a registered port. Port collision is possible")
        tcp_port = args.tcp_port
    else:
        tcp_port = 62994

    # Check broadcast port validity
    if args.broad_port:
        if args.broad_port < 0 or args.broad_port > 65535:
            print("Error: Argument 'broad_port' must be in the range 0 < x <= 65535")
            exit(1)
        if args.broad_port < 1024:
            print("Warning: Argument 'broad_port' is a well-defined port. This may require superuser permissions")
        elif args.broad_port < 49151:
            print("Warning: Argument 'broad_port' is a registered port. Port collision is possible")
        broad_port = args.broad_port

    # Establish server at specified port number and await a connection
    print(f"Establishing listening server on port {tcp_port}...")
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('', tcp_port))
    tcp_socket.listen(1)

    # Broadcasting mode enabled. Dispatch a thread to listen for requests
    if args.br or args.broad_port:
        broadcast_listener = threading.Thread(target=UDP_Broadcast, args=(tcp_port, broad_port,))
        broadcast_listener.start()

    # Serve indefinitely
    while True:
        tcp_conn, tcp_addr = tcp_socket.accept()
        # Service new connection
        print(f"Connection established by address {tcp_addr}")
        TCP_Connection_Handler(tcp_conn, args.rt)


def UDP_Broadcast(tcp_port, broad_port):
    # Response to be sent to the client if a broadcast is received
    resBody = {
        'port': tcp_port,
    }
    res = json.dumps(resBody).encode('utf-8')
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.bind(('', broad_port))
    print(f"Listening for broadcasts on {broad_port}")
    while(True):
        udp_msg, udp_addr = listener.recvfrom(1024)
        print(f"Broadcast message received by {udp_addr}. Replying...")
        listener.sendto(res, udp_addr)

# Handles TCP connections for handling active tests.
# Is NOT intended to be threaded
def TCP_Connection_Handler(tcp_conn, echo):
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

    # Bind UDP socket to an OS-specified port number
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', 0))

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
            print("Testing complete. Closing Connection...")
            tcp_conn.send(json.dumps(results).encode('utf-8') + b'\n')
            tcp_conn.close()
            udp_socket.close()
            return

        # Getting artificial loss value from config
        if round_config['loss'] > 1 or round_config['loss'] < 0:
            print("Error: Argument 'loss' must be in the range 0 <= x <= 1")
            tcp_conn.send(json.dumps("Error: Argument 'loss' must be in the range 0 <= x <= 1").encode('utf-8') + b'\n')
            tcp_conn.close()
            udp_socket.close()
            return
        loss = round_config['loss']

        # Testing has proceeded to the next round. Create arguments, spawn handler, and signal ready
        statistics = []
        stop_signal = False
        listener_thread = {}
        if echo == True:
            listener_thread = threading.Thread(target=UDP_Reply, args=(udp_socket, round_config['expected_payload'], statistics, loss, lambda: stop_signal,))
        else:
            listener_thread = threading.Thread(target=UDP_Listener, args=(udp_socket, round_config['expected_payload'], statistics, loss, lambda: stop_signal,))
        listener_thread.start()
        tcp_conn.send(json.dumps({'status': 'ready'}).encode('utf-8') + b'\n')

        start = time.time()

        # Await round completion JSON from client
        data = bytearray()
        byte = tcp_conn.recv(1)
        while byte != '':
            if b'\n' == byte:
                break
            data += byte
            byte = tcp_conn.recv(1)

        finish = time.time()
        diff = finish - start

        # Signal UDP listening thread to terminate and then await it
        stop_signal = True
        listener_thread.join()

        # Compute round results
        results.append(compute_Results(round_config, statistics, diff))

        # Signal client that server is ready for the next round
        tcp_conn.send(json.dumps({'status': 'ready'}).encode('utf-8') + b'\n')


def compute_Results(round_config, statistics, diff):
    
    print(round_config)
    packets_received, packets_mangled = statistics
    print(f'Packets mangled {packets_mangled}')
    if (round_config['packet_count'] > 0):
        lost_percent = (round_config['packet_count'] - packets_received) / round_config['packet_count'] * 100
    else:
        lost_percent = 0

    if(packets_received > 0):
        mangled_percent = 100 - ((packets_received - packets_mangled) / packets_received * 100)
    else:
        mangled_percent = 0

    rating = 'pass'
    if lost_percent > 1:
        rating = 'acceptable'
    if lost_percent > 7:
        rating = 'fail'

    return {
        'round': round_config['round'],
        'rate': round_config['rate'],
        'packets': round_config['packet_count'],
        'lost': lost_percent,
        'mangled': mangled_percent,
        'rating': rating,
        'duration': diff
    }

# Handles UDP listening on a separate thread so that the TCP connection can be monitored by main thread for status updates
# Param: udp_socket: The udp socket to be monitored
# Param: expected_byte: An integer representation of the expected byte value repeated in the payload
# Param: statistics: A list object consisting of the tuple [packets_received, packets_mangled]
# Param: loss: A float value that specifies the amount of articial loss to be inserted into the analysis
# Param: signal: A boolean that signifies whether the thread should terminate after a period of no new packets (should be passed as a lambda to avoid pass-by-value)
def UDP_Listener(udp_socket, expected_byte, statistics, loss, signal):

    packets_received = 0
    packets_mangled = 0
    payload = bytearray([expected_byte] * 9216)

    while True:
        udp_socket.settimeout(1)
        try:
            udp_msg = udp_socket.recv(9216)
            # If packet falls within artificial loss window, drop (ignore) it
            if(random.random() > loss):
                # If payload matches expected payload, just increment packet counter
                if(udp_msg == payload):
                    packets_received = packets_received + 1
                # Else, payload was mangled. Increment packet counter and magled packet counter
                else:
                    packets_received = packets_received + 1
                    packets_mangled = packets_mangled + 1
        except socket.timeout:
            if signal():
                statistics.append(packets_received)
                statistics.append(packets_mangled)
                return

def UDP_Reply(udp_socket, expected_byte, statistics, loss, signal):

    packets_received = 0
    packets_mangled = 0
    payload = bytearray([expected_byte] * 9216)

    while True:
        udp_socket.settimeout(1)
        try:
            udp_msg, udp_addr = udp_socket.recvfrom(9216)
            # If packet falls within artificial loss window, drop (ignore) it
            if(random.random() > loss):
                # If payload matches expected payload, just increment packet counter
                udp_socket.sendto(udp_msg, udp_addr)
                if(udp_msg == payload):
                    packets_received = packets_received + 1
                # Else, payload was mangled. Increment packet counter and magled packet counter
                else:
                    packets_received = packets_received + 1
                    packets_mangled = packets_mangled + 1

        except socket.timeout:
            if signal():
                statistics.append(packets_received)
                statistics.append(packets_mangled)
                return


if __name__ == "__main__":
    main()