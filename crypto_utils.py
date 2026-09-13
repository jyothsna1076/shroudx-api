# crypto_utils.py
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

def pad(text):
    padding_len = 16 - len(text) % 16
    return text + chr(padding_len) * padding_len

def unpad(text):
    padding_len = ord(text[-1])
    return text[:-padding_len]

def encrypt(text, key):
    key = key.ljust(32)[:32].encode('utf-8')
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_text = pad(text)
    encrypted = cipher.encrypt(padded_text.encode('utf-8'))
    
    return base64.b64encode(iv + encrypted).decode('utf-8')

def decrypt(encrypted_text, key):
    key = key.ljust(32)[:32].encode('utf-8')
    raw = base64.b64decode(encrypted_text)
    iv = raw[:16]
    encrypted = raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted).decode('utf-8')
    return unpad(decrypted)
