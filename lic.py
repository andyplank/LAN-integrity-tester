#!/usr/bin/python

# TODO: Server IP and Port is hardcoded to localhost. Need to make them dynamic based on parameter input (and perhaps even make it auto-find servers using UDP broadcast?)
# TODO: Handle Rate argument input (i.e. do we want to specify '1000' or '1kpbs', '1000000000' or '1gbps', etc.)
# TODO: Sleep Timer and Packet Size need to be amended (MacOS sends 1 packet per byte! ouch)
# TODO: Result table needs to be pretty printed a little better with zero padding

import argparse
import json
import random
import socket
import sys
import time
import traceback

def main():

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('rounds', type=int, help='The number of tranmission rounds to be performed (number of divisions of the transmission rate) (max 25)')
    parser.add_argument('rate', type=int, help='The maximum rate of data transfer to be incrementally tested up to (max 1gbps)')
    parser.add_argument('-a', dest='address', type=str, nargs='?', help='The IP address of the desired server')
    parser.add_argument('-p', dest='port', type=int, nargs='?', help='The port number of the desired server')
    parser.add_argument('-l', dest='loss', type=float, nargs='?', help='An artificial amount of loss to be added.')
    args = parser.parse_args()
    
    # Check argument validity
    if args.rounds < 1 or args.rounds > 25:
        print("Error: Argument 'rounds' must be in the range 0 < x <= 25")
        exit(1)

    # Check artificial loss argument
    loss = 0
    if args.loss:
        if args.loss > 1:
            print("Error: Argument 'loss' must be in the range 0 <= x <= 1")
            exit(1)
        if args.loss < 0:
            print("Error: Argument 'loss' must be in the range 0 <= x <= 1")
            exit(1)
        loss = args.loss

    # Determine round and datarate information
    max_rounds = args.rounds if args.rounds else 10
    max_rate = args.rate if args.rate else 1000000000
    increment = max_rate / max_rounds

    # Establish a connection to the remote server
    print("Establishing a connection to the test server...")
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect(('localhost', 62994))
    except:
        print("Failed to establish a connection to the server. Aborting...")
        traceback.print_exc()
        exit(1)
    print("Successfully established a connection to the test server.")

    print("Setting up testing environment...")
    try:
        # Create synchronization request and send to remote server as JSON
        request = {
            'status': 'synchronize',
        }
        tcp_socket.send(json.dumps(request).encode('utf-8') + b'\n')

        # Listen for server syn-ack response
        data = bytearray()
        byte = tcp_socket.recv(1)
        while byte != '':
            if b'\n' == byte:
                break
            data += byte
            byte = tcp_socket.recv(1)

        # Extract server's UDP port number from server response
        response = json.loads(data.decode('utf-8'))

        if 'status' not in response or response['status'] != 'synchronize-ack': 
            raise Exception('Server did not syn-ack')
            return

        udp_port = response['udp_port']

        # Create UDP connection to server at specified port
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except:
        print("Failed to establish testing environment. Aborting...")
        traceback.print_exc()
        exit(1)
    print("Successfully established testing environmnet.")

    # Establish storage for result data
    results = []

    print("Beginning testing procedure...")
    # Iterate over rounds
    current_round = 1
    while current_round <= max_rounds:
        print(f"Running round {current_round} at rate {current_round * increment}")
        # Compute amount of data to be sent given a 5 second duration
        current_rate = current_round * increment
        byte_count = int(current_rate * 5 / 8)
        # sleep_time = 5 / byte_count / 8
        sleep_time = 0
        print(f"Current Rate: {current_rate}, byte_count: {byte_count}, sleep_time: {sleep_time}")

        # Send server current round configuration JSON
        config = {
            'status': 'test_in_progress',
            'round': current_round,
            'rate': current_rate,
            'byte_count': byte_count,
            'loss': loss
        }

        tcp_socket.send(json.dumps(config).encode('utf-8') + b'\n')

        # Await server status response
        data = bytearray()
        byte = tcp_socket.recv(1)
        while byte != '':
            if byte == b'\n':
                break
            data += byte
            byte = tcp_socket.recv(1)
    
        if (json.loads(data.decode('utf-8'))['status'] != 'ready'):
            print("PANIC")
            exit(1)

        # Send UDP one byte at a time, with payload counting up from 0
        payload = bytearray(1)
        payload[0] = 0
        for x in range(byte_count):
            # print("payload:" + str(payload))
            udp_socket.sendto(payload, ('localhost', udp_port))
            payload[0] = (payload[0] + 1) % 255
            # time.sleep(sleep_time)

        # Signal server that round is complete
        tcp_socket.send(json.dumps({ 'status': 'round_complete'}).encode('utf-8') + b'\n')
        print(f"Round {current_round} complete")

        # Wait for server ready confirmation before proceeding to next round
        data = bytearray()
        byte = tcp_socket.recv(1)
        while byte != '':
            if b'\n' == byte:
                break
            data += byte
            byte = tcp_socket.recv(1)

        # Prepare for next testing round
        current_round = current_round + 1

    # Testing Complete.
    # Notify server that test is complete
    message = {
        'status': 'test_complete',
    }

    tcp_socket.send(json.dumps(message).encode('utf-8') + b'\n')

    # Retrieve results from server
    data = bytearray()
    byte = tcp_socket.recv(1)
    while byte != '':
        if b'\n' == byte:
            break
        data += byte
        byte = tcp_socket.recv(1)

    results = json.loads(data.decode('utf-8'))
    print(results)
    print("Testing Complete")
    print("Results:")
    print("--------------------------------------------------")
    print("Round    Rate       Lost      Rating")
    for result in results:
        print(f"{result['round']:02d}       {result['rate']}      {result['lost']}%     {result['rating']}")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()