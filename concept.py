import os
import fcntl
import struct
import select
import threading
import socket
import argparse
from queue import Queue, Empty
from pySX127x.LoRa import *
from pySX127x.board_config import BOARD
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

TUNSETIFF = 0x400454ca
IFF_TAP = 0x0002
IFF_NO_PI = 0x1000

# Queue for inter-thread communication
packet_queue = Queue()
ack_queue = Queue()

# Argument parsing
parser = argparse.ArgumentParser(description="LoRa Gateway/Client with Acknowledgment Protocol")
parser.add_argument('--mode', choices=['gateway', 'client'], required=True, help="Run as either 'gateway' or 'client'")
parser.add_argument('--device-id', type=int, required=True, help="Unique device ID (0 reserved for gateway)")
parser.add_argument('--ip', type=str, help="IP address to connect to (only for client mode)")
parser.add_argument('--lora-freq', type=float, default=915.0, help="LoRa frequency in MHz")
parser.add_argument('--lora-channel', type=float, default=1, help="LoRa channel specification (e.g., 1 for default)")
parser.add_argument('--retries', type=int, default=3, help="Number of retries for sending packets (only for client mode)")
parser.add_argument('--timeout', type=float, default=2.0, help="Timeout for ACK (seconds, only for client mode)")
parser.add_argument('--tap-device', type=str, default='tap0', help="TAP device name (only for client mode)")
parser.add_argument('--encryption-key', type=str, help="Encryption key for securing communication")
parser.add_argument('--lora-mode', choices=['LongFast', 'ShortSlow'], default='LongFast', help="Set the LoRa communication mode")
args = parser.parse_args()

# Unique ID and mode
DEVICE_ID = args.device_id
MODE = args.mode
RETRIES = args.retries
TIMEOUT = args.timeout
TAP_DEVICE = args.tap_device
ENCRYPTION_KEY = args.encryption_key.encode() if args.encryption_key else None
LORA_MODE = args.lora_mode

# LoRa setup
BOARD.setup()
lora = LoRa(verbose=False)
lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([0] * 6)

# Set the frequency based on the channel
if args.lora_channel == 1:
    lora.set_freq(args.lora_freq)
else:
    lora.set_freq(args.lora_freq + (args.lora_channel * 0.2))  # Adjust frequency based on channel

# Set mode parameters
if LORA_MODE == 'LongFast':
    lora.set_bw(BW.BW500)
    lora.set_spreading_factor(SF.SF7)
elif LORA_MODE == 'ShortSlow':
    lora.set_bw(BW.BW125)
    lora.set_spreading_factor(SF.SF12)

lora.set_pa_config(pa_select=1, max_power=0x04, output_power=0x0F)
lora.set_mode(MODE.STDBY)

# Gateway specific configuration
DEVICE_IP_MAP = {}  # Map LoRa device IDs to their IP addresses (only for gateway)
seq_num = 0  # Sequence number for packets


def encrypt_data(data, key):
    """Encrypt data using AES encryption."""
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(pad(data, AES.block_size))


def decrypt_data(data, key):
    """Decrypt data using AES encryption."""
    cipher = AES.new(key, AES.MODE_ECB)
    return unpad(cipher.decrypt(data), AES.block_size)


def encapsulate_packet(device_id, packet_type, sequence_num, data):
    """Encapsulate the data into a packet with a unified format including a sequence number."""
    if ENCRYPTION_KEY:
        data = encrypt_data(data, ENCRYPTION_KEY)
    payload_length = len(data)
    if payload_length > 251:
        raise ValueError("Payload too large to fit in the packet")
    packet = struct.pack('BBB', device_id, packet_type, payload_length + 1) + struct.pack('B', sequence_num) + data
    return packet


def on_rx_done():
    print("Received LoRa packet")
    lora.clear_irq_flags(RxDone=1)
    payload = lora.read_payload(nocheck=True)
    if len(payload) >= 4:
        device_id = payload[0]
        packet_type = payload[1]
        payload_length = payload[2]
        sequence_num = payload[3]
        data = bytes(payload[4:4 + (payload_length - 1)])

        if ENCRYPTION_KEY:
            data = decrypt_data(data, ENCRYPTION_KEY)

        if MODE == 'gateway':
            handle_gateway_rx(device_id, packet_type, sequence_num, data)
        elif MODE == 'client':
            handle_client_rx(device_id, packet_type, sequence_num, data)


def handle_gateway_rx(device_id, packet_type, sequence_num, data):
    """Handle received packets in gateway mode."""
    if packet_type == 0x01:  # Assuming packet type 0x01 is for data
        print(f"Data received from device {device_id}, Seq: {sequence_num}: {data}")
        # Send ACK with the same sequence number
        ack_packet = encapsulate_packet(DEVICE_ID, 0x03, sequence_num, b'')
        packet_queue.put(ack_packet)
        if device_id in DEVICE_IP_MAP:
            ip = DEVICE_IP_MAP[device_id]
            forward_packet_to_internet(ip, data)
        else:
            print(f"Unknown device ID: {device_id}")


def handle_client_rx(device_id, packet_type, sequence_num, data):
    """Handle received packets in client mode."""
    if device_id == DEVICE_ID and packet_type == 0x03:  # ACK packet
        print(f"ACK received from gateway for Seq: {sequence_num}")
        ack_queue.put(sequence_num)  # Notify that ACK was received with the specific sequence number


def forward_packet_to_internet(ip, data):
    """Forward the packet to the internet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, 80))  # Example: Connecting to port 80 on the target IP
        s.sendall(data)
        response = s.recv(2048)
        s.close()

        # Encapsulate the response and send it back to the device
        global seq_num
        response_packet = encapsulate_packet(DEVICE_ID, 0x02, seq_num, response)
        seq_num += 1
        packet_queue.put(response_packet)
    except Exception as e:
        print(f"Failed to forward packet to {ip}: {e}")


def read_thread():
    """Thread to handle encapsulated packets from LoRa devices."""
    while True:
        packet = packet_queue.get()
        if packet:
            print(f"Sending encapsulated packet over LoRa: {packet}")
            lora.write_payload(list(packet))
            lora.set_mode(MODE.TX)

            while lora.get_irq_flags()['tx_done'] == 0:
                pass  # Wait until the packet is sent

            lora.clear_irq_flags(TxDone=1)
            lora.set_mode(MODE.RXCONT)  # Set to receive mode after sending


def tap_interface_setup(tap_device):
    """Setup the TAP interface for communication."""
    tap = os.open('/dev/net/tun', os.O_RDWR)
    ifr = struct.pack('16sH', tap_device.encode(), IFF_TAP | IFF_NO_PI)
    fcntl.ioctl(tap, TUNSETIFF, ifr)
    return tap


def client_mode(tap):
    """Main loop for client mode."""
    global seq_num
    while True:
        r, _, _ = select.select([tap], [], [])
        for ready in r:
            packet = os.read(ready, 2048)
            print(f"Received packet on TAP: {packet}")
            encapsulated_packet = encapsulate_packet(DEVICE_ID, 0x01, seq_num, packet)
            success = send_with_ack(encapsulated_packet, seq_num)
            if not success:
                print(f"Failed to send packet after {RETRIES} retries, Seq: {seq_num}")
            seq_num += 1


def send_with_ack(packet, sequence_num):
    """Send a packet and wait for an ACK."""
    for attempt in range(RETRIES):
        packet_queue.put(packet)
        print(f"Sent packet with Seq: {sequence_num}, waiting for ACK (Attempt {attempt + 1}/{RETRIES})")
        try:
            ack_received = ack_queue.get(timeout=TIMEOUT)
            if ack_received == sequence_num:
                return True
        except Empty:
            print(f"No ACK received for Seq:
