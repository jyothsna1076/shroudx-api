import re
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import time

def generate_aes_key():
    key = get_random_bytes(32)  # 256-bit AES key
    return base64.b64encode(key).decode()  # return as shareable string

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
    
#converting a string to binary
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

#wrapping a string - adds a special unicode character(\ufeff - zero width non breaking space) at the beginning and end of every string
def wrap(text):
    return "\ufeff" + text + "\ufeff"

def unwrap(text):
    matches = re.findall("\ufeff(.*?)\ufeff", text, re.DOTALL)
    return matches[0] if matches else text  # If not wrapped, return as is

#convert binary to zero width characters
def binary_to_hidden(text):
    return (text.replace(' ', '\u2060') #word joiner
            .replace('0', '\u200B') #zero width space
            .replace('1', '\u200C')) 

def hidden_to_binary(text):
    binary = (text.replace('\u2060', ' ')  # WORD JOINER (U+2060) → ' '
                  .replace('\u200B', '0')  # ZERO WIDTH SPACE (U+200B) → '0'
                  .replace('\u200C', '1'))  # ZERO WIDTH NON-JOINER (U+200C) → '1'
    # binary = ' '.join([binary[i:i+8] for i in range(0, len(binary), 8)])
    return binary

def encode_stego_file(input_file, secret_message, output_file, expiry_seconds):
    with open(input_file, "r", encoding="utf-8") as file:
        cover_text = file.read()
    print(f"Text present in original file: {cover_text}")

    aes_key = generate_aes_key()
    print(f"Encryption Key (SAVE THIS!): {aes_key}")

    encrypted_secret = encrypt_secret(secret_message, aes_key)
    binary_secret = str_to_binary(encrypted_secret)

    embed_time = int(time.time())
    time_bits = format(embed_time, '032b')
    expiry_bits = format(expiry_seconds, '032b')

    full_binary = time_bits + expiry_bits + binary_secret

    hidden_data = binary_to_hidden(full_binary)
    stego_text = wrap(hidden_data) + cover_text

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(stego_text)
    
    print(f"Stego file saved as {output_file}")

    return aes_key  # so it can be stored or reused

def decode_stego_file(stego_file, output_file, user_key):
    #print("Opening stego file..")
    try:
        with open(stego_file, "r", encoding="utf-8") as file:
            stego_text = file.read()
            print("Start of file (repr):", repr(stego_text[:200]))
        print(f"Text present in stego file: {stego_text}")
            
        #print("Stego file read successfully!")
        #print(f"Raw Content (repr): {repr(stego_text)}")
    except Exception as e:
        print(f"Error reading stego file: {e}")
        return

    #print("Extracting hidden data...")
    extracted_hidden = unwrap(stego_text)
    if not extracted_hidden:
        print("No hidden message found! Exiting function.")
        return  # Exit if no hidden message is extracted

    extracted_binary = hidden_to_binary(extracted_hidden)

    try:
        embed_time = int(extracted_binary[:32], 2)
        expiry_seconds = int(extracted_binary[32:64], 2)
        current_time = int(time.time())

        if current_time - embed_time > expiry_seconds:
            print("Message expired!")
            return

        binary_encrypted = extracted_binary[64:]  # strip time + expiry
        encrypted_msg = binary_to_str(binary_encrypted)
        decrypted = decrypt_secret(encrypted_msg, user_key)

        if decrypted:
                with open(output_file, "w", encoding="utf-8") as file:
                    file.write(decrypted)
                print(f"\nDecoded and decrypted message saved as '{output_file}'")
                print(f"Final Message: {decrypted}")

    except Exception as e:
        print("Decryption failed.")

# Example
# decode_stego_file("/Users/pradeepikanori/Desktop/stego_output.txt", "/Users/pradeepikanori/Desktop/decoded_text.txt")
# secret_message = "Vadlamudi Jyothsna"
# encode_stego_file("/Users/pradeepikanori/Desktop/stego_file.txt", secret_message, "/Users/pradeepikanori/Desktop/stego_output.txt")
# decode_stego_file("/Users/pradeepikanori/Desktop/stego_output.txt", "/Users/pradeepikanori/Desktop/decoded_text.txt", '+mhkP8eHPY3LRons/rO8rywRXf4z1KoSWMnKSTNWb/4=')