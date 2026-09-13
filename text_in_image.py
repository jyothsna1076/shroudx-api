import cv2
import numpy as np
import secrets
from skimage.metrics import structural_similarity as ssim
import random

"""      ### LEVEL 1 IMPLEMENTATION OF TEXT IN IMAGE STEGANOGRAPHY ###

# Function to embed text into an image
def embed_text_LSB(image_path, text_file, output_path):
    image = cv2.imread(image_path)
    height, width, _ = image.shape
    max_bits = width * height * 3
    max_chars = max_bits // 8  
    with open(text_file, "r") as file:
        message = file.read()
   
    # Append a delimiter to mark the end of the message
    message += "#####"
    binary_message = ''.join(format(ord(char), '08b') for char in message)

    # Check if message fits
    if len(binary_message) > max_bits:
        print(f"Error: Message too long! Max {max_chars} characters can be embedded.")
        return
    
    data_index = 0
    message_length = len(binary_message)
    
    for row in image:
        for pixel in row:
            for channel in range(3):  
                if data_index < message_length:
                    pixel[channel] = (pixel[channel] & 254) | int(binary_message[data_index]) 
                    data_index += 1
                else:
                    break
    
    cv2.imwrite(output_path, image)
    print(f"Message embedded and saved as {output_path}")


# Function to extract text from an image
def extract_text_LSB(image_path, output_text_file):
   """ """ Extract hidden text from an image and save it to a file """"""
    image = cv2.imread(image_path)
    binary_message = ""
    
    for row in image:
        for pixel in row:
            for channel in range(3):  # Read RGB channels
                binary_message += str(pixel[channel] & 1)

    # Convert binary to text
    message = ""
    for i in range(0, len(binary_message), 8):
        byte = binary_message[i:i+8]
        char = chr(int(byte, 2))
        if message.endswith("#####"):  # Stop at delimiter
            message = message[:-5]
            break
        message += char

    with open(output_text_file, "w") as file:
        file.write(message)
    
    print(f"Extracted message saved as {output_text_file}") """

             ### level 2 implementation with random key generation


# Function to generate and save a random key
def generate_key():
    key = secrets.randbits(32) 
    with open("stego_key.txt", "w") as key_file:
        key_file.write(str(key))
    return key

# Function to read the stored key
def read_key():
    with open("stego_key.txt", "r") as key_file:
        return int(key_file.read())

# Function to embed text into an image using random pixel selection
def embed_text_random(image_path, text_file, output_path):
    import cv2
    import numpy as np
    import secrets

    image = cv2.imread(image_path)
    with open(text_file, "r", encoding="utf-8") as file:
        message = file.read()

    message += "#####"
    binary_message = ''.join(format(ord(char), '08b') for char in message)

    key = secrets.randbits(32)
    np.random.seed(key)
    pixel_indices = np.random.choice(image.size // 3, len(binary_message), replace=False)

    data_index = 0
    for i in pixel_indices:
        row = i // image.shape[1]
        col = i % image.shape[1]
        channel = data_index % 3
        image[row, col, channel] = (image[row, col, channel] & 254) | int(binary_message[data_index])
        data_index += 1

    cv2.imwrite(output_path, image)
    print(f"Message embedded successfully into {output_path}")
    print(f"Share this key securely: {key}")
    print(key)
    return output_path, key  # Person A can manually share this with Person B


def extract_text_random(image_path, output_text_file, key):
    import cv2
    import numpy as np

    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not read image.")
        return False

    np.random.seed(key)
    binary_message = ""
    pixel_indices = np.random.choice(image.size // 3, image.size // 3, replace=False)

    end_marker = "0010001100100011001000110010001100100011"  # Binary for '#####'
    end_marker_found = False

    for i in pixel_indices:
        row = i // image.shape[1]
        col = i % image.shape[1]
        channel = len(binary_message) % 3
        binary_message += str(image[row, col, channel] & 1)

        if binary_message.endswith(end_marker):
            binary_message = binary_message[:-len(end_marker)]
            end_marker_found = True
            break

    if not end_marker_found:
        print("Error: Incorrect key or corrupted image.")
        return False

    try:
        message = "".join(chr(int(binary_message[i:i+8], 2)) for i in range(0, len(binary_message), 8))
    except ValueError:
        print("Error: Decoding binary to text failed. Possibly corrupted data.")
        return False

    with open(output_text_file, "w", encoding="utf-8") as file:
        file.write(message)

    print(f"Message successfully extracted and saved to {output_text_file}")
    return True








def embed_text_random_expire(image_path, text_file, output_path, expiry_seconds):
    import cv2
    import numpy as np
    import time

    def generate_key():
        import random
        return random.randint(0, 2**31 - 1)

    key = generate_key()
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not read image.")
        return None

    with open(text_file, "r", encoding="utf-8") as file:
        message = file.read()

    # Convert timestamp and expiry_seconds to 32-bit binary
    timestamp_bin = format(int(time.time()), '032b')
    if expiry_seconds == -1:
        expiry_bin = '1' * 32  # 32-bit flag for no expiry
    else:
        expiry_bin = format(int(expiry_seconds), '032b')

    # Add end marker
    message += "#####"
    binary_message = timestamp_bin + expiry_bin + ''.join(format(ord(char), '08b') for char in message)

    if len(binary_message) > image.size:
        print("Error: Message too long to embed in image.")
        return None

    # Embed using random pixels with key as seed
    np.random.seed(key)
    pixel_indices = np.random.choice(image.size // 3, len(binary_message), replace=False)

    for data_index, bit in enumerate(binary_message):
        i = pixel_indices[data_index]
        row = i // image.shape[1]
        col = i % image.shape[1]
        channel = data_index % 3
        image[row, col, channel] = (image[row, col, channel] & 254) | int(bit)

    cv2.imwrite(output_path, image)
    print(f"Message embedded successfully into {output_path}")
    print(key)
    return output_path, key



def extract_text_random_expire(image_path, output_text_file, key):
    import cv2
    import numpy as np
    import time

    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not read image.")
        return False

    np.random.seed(key)
    binary_message = ""
    pixel_indices = np.random.choice(image.size // 3, image.size // 3, replace=False)

    end_marker = "0010001100100011001000110010001100100011"  # Binary of '#####'
    end_marker_found = False

    for i in pixel_indices:
        row = i // image.shape[1]
        col = i % image.shape[1]
        channel = len(binary_message) % 3
        binary_message += str(image[row, col, channel] & 1)

        if binary_message.endswith(end_marker):
            binary_message = binary_message[:-len(end_marker)]
            end_marker_found = True
            break

    if not end_marker_found:
        print("Error: End marker not found. Possibly wrong key or corrupted data.")
        return False

    try:
        timestamp_bits = binary_message[:32]
        expiry_bits = binary_message[32:64]
        embed_time = int(timestamp_bits, 2)
        expiry_seconds = int(expiry_bits, 2)
        current_time = int(time.time())

        if expiry_seconds != 2**32 - 1:  # If it's not the "no expiry" flag
             if current_time - embed_time > expiry_seconds:
                print("Error: Message has expired and cannot be extracted.")
                return False

        binary_message = binary_message[64:]  # Remove timestamp and expiry info

        message = "".join(chr(int(binary_message[i:i+8], 2)) for i in range(0, len(binary_message), 8))
    except ValueError:
        print("Error: Binary decoding failed.")
        return False

    with open(output_text_file, "w", encoding="utf-8") as file:
        file.write(message)

    print(f"Message successfully extracted and saved to {output_text_file}")
    return True


# Compute PSNR
def compute_psnr(original, stego):
    mse = np.mean((original - stego) ** 2)
    if mse == 0:
        return float('inf')  # No difference
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr

# Compute SSIM
def compute_ssim(original, stego):
    ssim_value = ssim(original, stego, data_range=stego.max() - stego.min(), multichannel=True)
    return ssim_value

# Compute Hamming Distance
def compute_hamming_distance(original, stego):
    original_bits = np.unpackbits(original.flatten())
    stego_bits = np.unpackbits(stego.flatten())
    return np.sum(original_bits != stego_bits)

# Evaluate steganography
def evaluate_steganography(original_image, stego_image):
    original = cv2.imread(original_image)
    stego = cv2.imread(stego_image)

    gray_original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    gray_stego = cv2.cvtColor(stego, cv2.COLOR_BGR2GRAY)

    psnr_value = compute_psnr(original, stego)
    ssim_value = compute_ssim(gray_original, gray_stego)
    hamming_value = compute_hamming_distance(original, stego)

    print(f"PSNR: {psnr_value:.2f} dB")
    print(f"SSIM: {ssim_value:.4f}")
    print(f"Hamming Distance: {hamming_value}")

    return {
        "psnr": round(psnr_value, 2),
        "ssim": round(ssim_value, 4),
        "hamming": round(hamming_value, 2)
    }


# File paths
original_image = "butter.jpg"
text_file = "abc.txt"
decoded_text_file = "decoded_abc.txt"
stego_image = "static/outputs/encoded_butter.png"

# Embed and evaluate
"""embed_text_LSB(original_image, text_file, stego_image)

extract_text_LSB(stego_image, decoded_text_file)

print("for the LSB technique using rgb least bit manipulation method, the performance metrics are:")
evaluate_steganography(original_image, stego_image)

embed_text_random(original_image, text_file, stego_image)
extract_text_random(stego_image, decoded_text_file,key) 

print("for the LSB technique using rgb random bit manipulation method, the performance metrics are:")
evaluate_steganography(original_image, stego_image)
"""
