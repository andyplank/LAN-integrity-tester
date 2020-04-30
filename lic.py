#!/usr/bin/python3

import argparse
import json
import random
import socket
import sys
import time
import traceback
import threading
from tabulate import tabulate

def main():

    # Default port to broadcast to
    broad_port = 4322
    brp_help = f'The port number that the server will listen for broadcasts on. Default is {broad_port}'

    # Parse required arguments
    parser = argparse.ArgumentParser(description='LAN Integrity Tester Client')
    parser.add_argument('rounds', type=int, help='The number of tranmission rounds to be performed (number of divisions of the transmission rate) (max 25)')
    parser.add_argument('rate', type=int, help='The maximum rate of data transfer to be incrementally tested up to in mbps (max 1gbps)')
    parser.add_argument('-a', dest='address', type=str, nargs='?', help='The IP address of the desired server')
    parser.add_argument('-p', dest='port', type=int, nargs='?', help='The port number of the desired server')
    parser.add_argument('-l', dest='loss', type=float, nargs='?', help='An artificial amount of loss to be added.')
    parser.add_argument('-rt', action='store_true', help='A flag to enable round trip mode.')    
    parser.add_argument('-br', action='store_false', help='A flag to disable UDP broadcast to find the server.')    
    parser.add_argument('-brp', dest='broad_port', type=int, nargs='?', help=brp_help)
    args = parser.parse_args()

    # Check round validity
    if args.rounds:
        if args.rounds < 1 or args.rounds > 25:
            print("Error: Argument 'rounds' must be in the range 1 <= x <= 25")
            exit(1)
        else:
            rounds = args.rounds
    else:
        rounds = 10


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

    # Check artificial loss validity
    loss = 0
    if args.loss:
        if args.loss > 1:
            print("Error: Argument 'loss' must be in the range 0 <= x <= 1")
            exit(1)
        if args.loss < 0:
            print("Error: Argument 'loss' must be in the range 0 <= x <= 1")
            exit(1)
        loss = args.loss

    if args.rate < 1 or args.rate > 1000:
        print("Error: Argument 'rate' must be in the range 1 <= x <= 1000")
        exit(1)
    else:
        max_rate = args.rate*1000000 if args.rate else 1000000

    # Determine round and datarate information
    increment = max_rate / rounds

    if increment < 9216*8:
        print("Error: Decrease the number of rounds or increase the max data rate.")
        exit(1)

    # Check the max rate is not over 1 gbps
    if max_rate > 1000000000:
        print("Error: Data transfer rate is over 1 gbps.")
        exit(1)

    # Calculate the increment between each round
    increment = max_rate / rounds

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
            broadcast.sendto(b'Hello', ('<broadcast>', broad_port))
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
            tcp_socket.close()
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
    results_client = []

    print("Beginning testing procedure...\n")
    # Iterate over rounds
    current_round = 1
    while current_round <= rounds:
        print(f"Running round {current_round} of {rounds}...")

        # Compute random payload value
        payload_byte = random.randint(0, 255)
        payload = bytearray([payload_byte] * 9216)
    
        # Compute round rate, total bytes
        current_rate = current_round * increment
        packet_count = int(current_rate / 8 / 9216) 
        sleep_time = 1 / packet_count

        print(f"Current_rate is {current_rate}")
        print(f"packet_count is {packet_count}")
        print(f"sleep_time is {sleep_time}") 

        # Send server current round configuration JSON
        config = {
            'status': 'test_in_progress',
            'round': current_round,
            'rate': current_rate/1000000,
            'packet_count': packet_count,
            'expected_payload': payload_byte,
            'loss': loss
        }

        tcp_socket.send(json.dumps(config).encode('utf-8') + b'\n')

        # Wait for server response
        data = bytearray()
        byte = tcp_socket.recv(1)
        while byte != '':
            if byte == b'\n':
                break
            data += byte
            byte = tcp_socket.recv(1)

        # Check response code
        if (json.loads(data.decode('utf-8'))['status'] != 'ready'):
            print("PANIC")
            exit(1)

        listener_thread = {}
        statistics = []
        if args.rt:
            stop_signal = False
            listener_thread = threading.Thread(target=UDP_Listener, args=(udp_socket, payload, statistics, lambda: stop_signal,))
            listener_thread.start()

        start = time.time()

        # Send UDP 9216 bytes at a time, with payload containing a random duplicated byte
        for x in range(packet_count):
            udp_socket.sendto(payload, (address, udp_port))
            time.sleep(sleep_time)

        # Signal server that round is complete
        tcp_socket.send(json.dumps({ 'status': 'round_complete'}).encode('utf-8') + b'\n')
        print(f"Round {current_round} complete")

        # Wait for server response
        data = bytearray()
        byte = tcp_socket.recv(1)
        while byte != '':
            if b'\n' == byte:
                break
            data += byte
            byte = tcp_socket.recv(1)

        finish = time.time()
        diff = finish - start

        # If running in RT mode then append client results
        if args.rt:
            stop_signal = True
            listener_thread.join()
            results_client.append(compute_Results(config, statistics, diff))

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

    # Close connection
    tcp_socket.close()
    udp_socket.close()

    # Print the results of the test
    print("\n")
    print("Results from server:")
    header = {'round': "Round", 'rate':"Rate (mbps)", 'packets':"Packets", 'lost':"Lost (%)", 'mangled':"Mangled (%)", 'rating':"Rating", 'duration':"Duration"}
    print(tabulate(results, headers=header, tablefmt="grid"))

    # Print RT results if in RT mode
    if args.rt:
        print("Results on client:")
        print(tabulate(results_client, headers=header, tablefmt="grid"))


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
def UDP_Listener(udp_socket, expected_byte, statistics, signal):

    packets_received = 0
    packets_mangled = 0

    while True:
        udp_socket.settimeout(1)
        try:
            # If packet falls within artificial loss window, drop (ignore) it
                # If payload matches expected payload, just increment packet counter
            udp_msg = udp_socket.recv(9216)
            if(udp_msg == expected_byte):
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
