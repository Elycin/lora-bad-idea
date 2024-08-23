
# LoRa Gateway/Client for Internet Connectivity

This project provides a Python-based implementation of a LoRa gateway and client for transmitting internet connectivity over LoRa. The system allows multiple LoRa devices to communicate through a central gateway, which forwards packets to the internet and vice versa. The system supports acknowledgment (ACK) protocols, channel specification, encryption, and different LoRa communication modes.

## Features

- **Gateway and Client Modes**: The script can be run as either a gateway or a client, with different behaviors in each mode.
- **Acknowledgment Protocol**: Ensures reliable communication by confirming the receipt of packets.
- **Channel Specification**: Allows the selection of different channels for communication.
- **LoRa Encryption**: Supports AES encryption at the LoRa hardware level using a user-specified key.
- **Flexible LoRa Modes**: Offers different modes such as LongFast and ShortSlow, configuring bandwidth and spreading factor accordingly.
- **TAP Device Integration**: Supports integration with TAP devices for networking.

## Requirements

- Python 3.x
- LoRa hardware supported by `pySX127x`
- `pySX127x` library
- Linux system with support for TAP interfaces

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/LoRa-Internet-Bridge.git
   cd LoRa-Internet-Bridge
   ```

2. **Install dependencies**:
   Install the required Python libraries:
   ```bash
   pip install pySX127x pycryptodome
   ```

3. **Set up LoRa hardware**:
   Ensure your LoRa hardware is correctly set up and connected to your system.

## Usage

### Running the Gateway

To run the script in gateway mode, use the following command:

```bash
python lora_gateway_client.py --mode gateway --device-id 0 --lora-freq 915.0 --lora-channel 1 --encryption-key "0123456789abcdef0123456789abcdef" --lora-mode LongFast
```

- `--mode gateway`: Specifies that the script should run as a gateway.
- `--device-id 0`: The device ID for the gateway (reserved as 0).
- `--lora-freq 915.0`: Base frequency in MHz.
- `--lora-channel 1`: Channel number.
- `--encryption-key "0123456789abcdef0123456789abcdef"`: 16-byte AES encryption key as a hex string.
- `--lora-mode LongFast`: Specifies the LoRa communication mode.

### Running the Client

To run the script in client mode, use the following command:

```bash
python lora_gateway_client.py --mode client --device-id 1 --ip 192.168.1.100 --tap-device tap0 --lora-freq 915.0 --lora-channel 1 --encryption-key "0123456789abcdef0123456789abcdef" --lora-mode LongFast
```

- `--mode client`: Specifies that the script should run as a client.
- `--device-id 1`: Unique device ID for this client (non-zero).
- `--ip 192.168.1.100`: IP address to connect to (used by the gateway to forward traffic).
- `--tap-device tap0`: Specifies the TAP device name.
- `--lora-freq 915.0`: Base frequency in MHz.
- `--lora-channel 1`: Channel number.
- `--encryption-key "0123456789abcdef0123456789abcdef"`: 16-byte AES encryption key as a hex string.
- `--lora-mode LongFast`: Specifies the LoRa communication mode.

### Additional Options

- `--retries`: Number of retries for sending packets (client mode only).
- `--timeout`: Timeout in seconds for waiting for an ACK (client mode only).

## Example

Start the gateway:

```bash
python lora_gateway_client.py --mode gateway --device-id 0 --lora-freq 915.0 --lora-channel 1 --encryption-key "0123456789abcdef0123456789abcdef" --lora-mode LongFast
```

Start a client:

```bash
python lora_gateway_client.py --mode client --device-id 1 --ip 192.168.1.100 --tap-device tap0 --lora-freq 915.0 --lora-channel 1 --encryption-key "0123456789abcdef0123456789abcdef" --lora-mode LongFast
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please submit issues or pull requests for any improvements or features you would like to see.

## Acknowledgments

- The `pySX127x` library for LoRa communication in Python.
- The Open Source community for tools and inspiration.
