# Firmware Server Demo

## HTTP Server Demo

### Start Firmware Server

Navigate to your firmware-server directory and run:

```bash
cd secure_update_infrastructure-main/firmware-server
python3 firmware_server_http.py
```

### Create and Sign Manifest

Create SUIT manifest:

```bash
suit-tool create -i examples/example1.json -o example1.suit -c 'file=../firmware-server/firmware/file1.bin,inst=[00],uri=http://example.com/file1.bin'
suit-tool sign -m example1.suit -k private_key.pem -o example_slab_signed.suit
```

### Run SUIT Parser

Navigate to your SUIT Parser directory and extract image:

```bash
cd secure_update_consumer-main/SUIT-Parser
out/secure_update extract-image ../examples/example_slab_signed.suit
```

### Modifications

Modify the following functions in `Stubs.c` as needed:

* `suit_platform_do_fetch`
* `fetch_http_image`
* `fetch_coap_image`

---

## COAP Server Demo

### Install Dependencies

Install libcoap development package:

```bash
sudo apt-get install libcoap3-dev
```

Install Aiocoap Python package:

```bash
pip3 install --upgrade "aiocoap[all]"
```

Further details: [Aiocoap Installation Guide](https://aiocoap.readthedocs.io/en/latest/installation.html)

### Start COAP Server

Run the Aiocoap fileserver:

```bash
aiocoap-fileserver firmware
```

### Update Manifest JSON

Modify your manifest JSON component to use the COAP protocol:

```json
"components" : [
    {
        "install-id" : ["00"],
        "install-digest": {
            "algorithm-id": "sha256",
            "digest-bytes": "00112233445566778899aabbccddeeff0123456789abcdeffedcba9876543210"
        },
        "install-size" : 8,
        "uri": "coap://example.com/file1.bin"
    }
]
```

### Create and Sign COAP Manifest

Generate and sign the COAP manifest:

```bash
suit-tool create -i examples/example1.json -o example_slab_coap.suit -c 'file=../firmware-server/firmware/file1.bin,inst=[00],uri=coap://example.com/file1.bin'
suit-tool sign -m example_slab_coap.suit -k private_key.pem -o example_slab_coap_sign.suit
```

### Run SUIT Parser

Extract image using the SUIT parser:

```bash
out/secure_update extract-image ../examples/example_slab_coap_sign.suit
```
