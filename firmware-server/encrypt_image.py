import os
import argparse
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Use a fixed salt for key derivation for this example.
# In a real system, this might be handled differently.
SALT = b'suit-encryption-salt'
KEY_LENGTH_BYTES = 32 # For AES-256
NONCE_LENGTH_BYTES = 12
TAG_LENGTH_BYTES = 16

def derive_key(secret: str) -> bytes:
    """Derives a 32-byte key from a secret string using SHA-256."""
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(SALT) # Use a salt to prevent simple rainbow table attacks
    digest.update(secret.encode('utf-8'))
    return digest.finalize()

def encrypt_file(input_path: str, output_path: str, secret: str):
    """
    Encrypts the input file and writes the nonce, tag, and ciphertext to the output file.
    """
    print(f"Deriving encryption key from secret...")
    # 1. Derive a 32-byte (256-bit) key from the provided secret.
    key = derive_key(secret)

    # 2. Initialize AES-GCM with the derived key.
    aesgcm = AESGCM(key)

    # 3. Generate a cryptographically secure random nonce.
    # The nonce MUST be unique for every encryption with the same key.
    nonce = os.urandom(NONCE_LENGTH_BYTES)
    print(f"Generated {NONCE_LENGTH_BYTES}-byte nonce.")

    print(f"Reading plaintext from '{input_path}'...")
    # 4. Read the plaintext file content.
    with open(input_path, 'rb') as f:
        plaintext = f.read()

    print(f"Encrypting {len(plaintext)} bytes of data...")
    # 5. Encrypt the data. AES-GCM produces the ciphertext and the authentication tag together.
    # The tag is appended to the ciphertext automatically by this library.
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, None) # No additional authenticated data

    # 6. Write the nonce, and the combined ciphertext+tag to the output file.
    # Output Format: [ nonce | ciphertext | tag ]
    # Note: The library we use appends the tag to the ciphertext.
    # We will need to separate it during decryption.
    # Let's be more explicit and handle them separately for clarity.
    
    ciphertext = ciphertext_and_tag[:-TAG_LENGTH_BYTES]
    tag = ciphertext_and_tag[-TAG_LENGTH_BYTES:]

    print(f"Writing encrypted data to '{output_path}'...")
    with open(output_path, 'wb') as f:
        f.write(nonce)
        f.write(tag)
        f.write(ciphertext)

    print("\nEncryption successful! ✅")
    print(f"Output file format: [{NONCE_LENGTH_BYTES}-byte nonce][{TAG_LENGTH_BYTES}-byte tag][{len(ciphertext)}-byte ciphertext]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encrypt a firmware image for SUIT update.")
    parser.add_argument("input_file", help="The path to the input binary file to encrypt.")
    parser.add_argument("output_file", help="The path to write the encrypted output file.")
    parser.add_argument("--secret", required=True, help="The shared secret string for encryption.")
    args = parser.parse_args()

    try:
        encrypt_file(args.input_file, args.output_file, args.secret)
    except Exception as e:
        print(f"\nAn error occurred: {e} ❌")