import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import time

# === AES UTILS ===
def generate_aes_key():
    key = get_random_bytes(32)  # 256-bit AES key
    return base64.b64encode(key).decode()  # shareable string

def decode_aes_key(key_b64):
    return base64.b64decode(key_b64.encode())

def encrypt_secret(secret, key_b64):
    key = decode_aes_key(key_b64)
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(secret.encode(), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode()
    ct = base64.b64encode(ct_bytes).decode()
    return iv + ":" + ct

def decrypt_secret(encrypted_text, key_b64):
    try:
        key = decode_aes_key(key_b64)
        iv_str, ct_str = encrypted_text.split(":")
        iv = base64.b64decode(iv_str)
        ct = base64.b64decode(ct_str)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode()
    except Exception as e:
        print("Decryption failed:", e)
        return None
    
def str_to_binary(text):
    bin_list = []
    for i in range(len(text)):
        bin_list.append(bin(ord(text[i]))[2:])  # Convert char to ASCII → Binary (remove '0b' prefix)
    return ' '.join(bin_list)

#converting a binary to string
def binary_to_str(bin_text):
    binary_values = bin_text.split()  # Split space-separated binary

    decoded_text = []
    for b in binary_values:
        try:
            decoded_text.append(chr(int(b, 2)))  # Convert binary to character
        except ValueError:
            continue  # Ignore invalid binary chunks instead of breaking

    return ''.join(decoded_text)  # Return the full decoded string

# === CUSTOM ENCRYPTION ===
def caesar_transform(text):
    result = ""
    for char in text:
        if char.isalpha():
            if char.isupper():
                result += chr((ord(char)+23-65) % 26 + 65)
            else:
                result += chr((ord(char)+23-97) % 26 + 97)
        elif char.isdigit():
            result += chr((ord(char) - ord('0') + 5) % 10 + ord('0'))
        else:
            result += char
    return result

def caesar_reverse(text):
    result = ""
    for char in text:
        if char.isalpha():
            if char.isupper():
                result += chr((ord(char)-23-65) % 26 + 65)
            else:
                result += chr((ord(char)-23-97) % 26 + 97)
        elif char.isdigit():
            result += chr((ord(char) - ord('0') - 5) % 10 + ord('0'))
        else:
            result += char
    return result

def encrypt(secret_file, output_file, expiry_seconds):
    with open(secret_file, "r", encoding="utf-8") as file:
        text = file.read()

    # Caesar + AES encryption
    transformed = caesar_transform(text)
    aes_key = generate_aes_key()
    encrypted = encrypt_secret(transformed, aes_key)

    # Add timestamp and expiry
    embed_time = int(time.time())
    timestamp_str = str(embed_time).zfill(10)
    expiry_str = str(expiry_seconds).zfill(6)

    final_data = f"{timestamp_str}|{encrypted}|{expiry_str}"

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(final_data)

    print(f"Encrypted file saved as '{output_file}'")

    return aes_key


def decrypt(secret_file, output_file, user_key):
    try:
        with open(secret_file, "r", encoding="utf-8") as file:
            content = file.read()

        # Parse metadata
        parts = content.split("|", 2)
        if len(parts) != 3:
            return False, "Invalid file format. Metadata missing."

        timestamp_str, encrypted_text, expiry_str = parts
        embed_time = int(timestamp_str)
        expiry_seconds = int(expiry_str)
        current_time = int(time.time())

        # Expiry check
        if current_time - embed_time > expiry_seconds:
            return False, "Message has expired! Decryption aborted."

        # AES decryption
        decrypted = decrypt_secret(encrypted_text, user_key)
        if decrypted is None:
            return False, "Decryption failed. Check the key."

        # Reverse Caesar
        original = caesar_reverse(decrypted)

        with open(output_file, "w", encoding="utf-8") as file:
            file.write(original)

        return True, original  # success
    except Exception as e:
        return False, f"Error during decryption: {e}"  # fail

# key = encrypt('/Users/pradeepikanori/Desktop/stego_file.txt', '/Users/pradeepikanori/Desktop/stego_output.txt', 150)
# print(key)

# decrypt('/Users/pradeepikanori/Desktop/stego_output.txt', '/Users/pradeepikanori/Desktop/input_file.txt', 'khXoa60nBDwuiNWkQ6DfFJzVqoFVsee0eVdCGuaUw4c=')
