#!/usr/bin/python

# TODO: Sleep Timer and Packet Size need to be amended (MacOS sends 1 packet per byte! ouch)

import argparse
import json
import random
import socket
import sys
import time
import traceback
from tabulate import tabulate

def main():

    # Default port to broadcast to
    broad_port = 4322

    brp_help = f'The port number that the server will listen for broadcasts on. Default is {broad_port}'

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('rounds', type=int, help='The number of tranmission rounds to be performed (number of divisions of the transmission rate) (max 25)')
    parser.add_argument('rate', type=int, help='The maximum rate of data transfer to be incrementally tested up to (max 1gbps)')
    parser.add_argument('-a', dest='address', type=str, nargs='?', help='The IP address of the desired server')
    parser.add_argument('-p', dest='port', type=int, nargs='?', help='The port number of the desired server')
    parser.add_argument('-l', dest='loss', type=float, nargs='?', help='An artificial amount of loss to be added.')
    parser.add_argument('-uni', dest='unit', type=str, nargs='?', help='The desired unit for rate in kbps, mbps, or gbps. Default is bytes')
    parser.add_argument('-br', action='store_true', help='A flag to use UDP broadcast to find the server.')    
    parser.add_argument('-brp', dest='broad_port', type=int, nargs='?', help=brp_help)
    args = parser.parse_args()

    # Check argument validity
    if args.rounds < 1 or args.rounds > 25:
        print("Error: Argument 'rounds' must be in the range 0 < x <= 25")
        exit(1)

    # Check argument validity
    if (args.unit != 'kbps'
        and args.unit != 'mbps'
        and args.unit != 'gbps'):
        print("Error: Argument 'unit' must be either kbps, mbps, or gbps")
        exit(1)

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

    # Calculate the new data transfer rate
    if args.unit:
        multipler = 1
        if args.unit == 'kbps':
            multiplier = 1000
        if args.unit == 'mbps':
            multiplier = 1000000
        if args.unit == 'gbps':
            multiplier = 1000000000
        max_rate = max_rate * multiplier

    # Check the max rate is not over 1 gbps
    if max_rate > 1000000000:
        print("Error: Data transfer rate is over 1 gbps.")
        exit(1)

    # Calculate the increment between each round
    increment = max_rate / max_rounds

    # Extract optional address and port argument
    address = args.address if args.address else 'localhost'
    port = args.port if args.port else 62994
    
    # Running in broadcast mode so we have to locate the server
    if args.br:
        print('Broadcast mode enabled. Attempting to locate the server...')
        broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast.settimeout(1)
        reply = False
        # Broadcast the message 10 times and wait 1 s for a reply each time
        for i in range(10):
            broadcast.sendto(b'Hello', ('<broadcast>', 4322))
            try:
                udp_msg, udp_addr = broadcast.recvfrom(1024)
                response = json.loads(udp_msg.decode('utf-8'))
                address = udp_addr[0]
                try:
                    port = response['port']
                except KeyError:
                    print("Error: invalid response from server. Try a different broadcast port")
                    continue
                print(f'Server located at {address}:{port}')
                reply = True
                broadcast.close()
                break
            except socket.timeout:
                continue
        # If no reply was received from the server then terminate
        if not reply:
            print("Broadcast failed. No response was received from the server")
            exit(1)        

    print(address)
    print(port)

    # Establish a connection to the remote server
    print("Establishing a connection to the test server...")
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((address, port))
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
            udp_socket.sendto(payload, (address, udp_port))
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

    # Print the results of the test
    header = {'round': "Round", 'rate':"Rate (bytes)", 'lost':"Lost (%)", 'rating':"Rating"}
    print(tabulate(results, headers=header, tablefmt="grid"))


if __name__ == "__main__":
    main()
