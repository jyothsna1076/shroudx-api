import os
import time
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from crypto_utils import encrypt, decrypt
from scipy.io import wavfile

import text_in_image
import image_in_image2
import text_in_text_caecip
import text_in_text_zwc
from audio_in_image import Start_Encode, Start_Decode
from logger import log_event

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.secret_key = "your-very-secret-key"
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

AES_PASSWORD = os.environ.get('AES_SECRET_PASSWORD', 'your-secret-password')

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    return jsonify({'success': False, 'error': 'File too large. Max size is 10MB.'}), 413

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/text-in-image/encode', methods=['POST'])
def text_in_image_encode():
    try:
        image_file = request.files.get("image")
        text_file = request.files.get("text")
        if not image_file or not text_file:
            return jsonify({'success': False, 'error': 'Please upload an image and a text file.'}), 400

        image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
        text_path = os.path.join(UPLOAD_FOLDER, text_file.filename)
        image_file.save(image_path)
        text_file.save(text_path)

        encoded_random_path = os.path.join(OUTPUT_FOLDER, "encoded_random.png")
        expiry_str = request.form.get("expiry_time", "").strip()

        try:
            expiry_seconds = int(expiry_str) if expiry_str else None
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid expiry time format.'}), 400

        start_time = time.time()
        if expiry_seconds:
            encoded_random_path, key = text_in_image.embed_text_random_expire(image_path, text_path, encoded_random_path, expiry_seconds)
            log_event("TEXT_ENCODE", f"Image: {image_file.filename}, Text: {text_file.filename}, Expiry: {expiry_seconds}s")
        else:
            encoded_random_path, key = text_in_image.embed_text_random(image_path, text_path, encoded_random_path)
            log_event("TEXT_ENCODE", f"Image: {image_file.filename}, Text: {text_file.filename}, No expiry")
        end_time = time.time()
        embed_time = round(end_time - start_time, 4)

        key_used = encrypt(str(key), AES_PASSWORD)

        return jsonify({
            "success": True,
            "encoded_image_url": "/api/download/encoded_random.png",
            "key": key_used,
            "embed_time": embed_time
        })
    except Exception as e:
        log_event("TEXT_ENCODE_FAILED", f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/text-in-image/decode', methods=['POST'])
def text_in_image_decode():
    try:
        image_file = request.files.get("stego_image")
        encrypted_key_str = request.form.get("secret_key", "").strip()

        if not image_file or not encrypted_key_str:
            return jsonify({'success': False, 'error': 'Stego image and secret key are required.'}), 400

        try:
            key_str = decrypt(encrypted_key_str, AES_PASSWORD)
            key = int(key_str)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Invalid or corrupted key: {e}'}), 400

        image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
        image_file.save(image_path)
        decoded_text_path = os.path.join(OUTPUT_FOLDER, "decoded.txt")

        start_decode = time.time()
        result = text_in_image.extract_text_random_expire(image_path, decoded_text_path, key)
        end_decode = time.time()
        decode_time = round(end_decode - start_decode, 4)

        if result is False:
            log_event("TEXT_DECODE_FAILED", f"Image: {image_file.filename}, Key: {key_str[:4]}****")
            return jsonify({'success': False, 'error': 'Message expired or invalid stego image/key.'}), 400

        log_event("TEXT_DECODE_SUCCESS", f"Image: {image_file.filename}, Key: {key_str[:4]}****")
        return jsonify({
            "success": True,
            "decoded_text_url": "/api/download/decoded.txt",
            "decode_time": decode_time
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-in-image/encode', methods=['POST'])
def image_in_image_encode():
    try:
        cover_img = request.files.get("cover_image")
        secret_img = request.files.get("secret_image")
        expiry_time = request.form.get("expiry_time")

        if not cover_img or not secret_img or not expiry_time:
            return jsonify({'success': False, 'error': 'Cover image, secret image, and expiry time are required.'}), 400

        try:
            expiry_seconds = int(expiry_time)
        except ValueError:
            return jsonify({'success': False, 'error': 'Expiry time must be a valid integer.'}), 400

        cover_path = os.path.join(UPLOAD_FOLDER, cover_img.filename)
        secret_path = os.path.join(UPLOAD_FOLDER, secret_img.filename)
        stego_path = os.path.join(OUTPUT_FOLDER, "stego_image.png")

        cover_img.save(cover_path)
        secret_img.save(secret_path)

        start_time = time.time()
        secret_info, level, x = image_in_image2.Start_Encode(cover_path, secret_path, stego_path)
        end_time = time.time()
        embed_time = round(end_time - start_time, 4)

        encode_timestamp = int(time.time())
        key_values = secret_info + [level, encode_timestamp, expiry_seconds, x]
        key_string = ','.join(map(str, key_values))
        encrypted_key = encrypt(key_string, AES_PASSWORD)

        log_event("IMAGE_ENCODE", f"Cover: {cover_img.filename}, Secret: {secret_img.filename}, Expiry: {expiry_seconds}s")
        return jsonify({
            "success": True,
            "encoded_image_url": "/api/download/stego_image.png",
            "encrypted_key": encrypted_key,
            "embed_time": embed_time
        })
    except Exception as e:
        log_event("IMAGE_ENCODE_FAILED", f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-in-image/decode', methods=['POST'])
def image_in_image_decode():
    try:
        stego_img = request.files.get("stego_image")
        encrypted_key_input = request.form.get("manual_key")

        if not stego_img or not encrypted_key_input:
            return jsonify({'success': False, 'error': 'Stego image and manual key are required.'}), 400

        stego_path = os.path.join(UPLOAD_FOLDER, stego_img.filename)
        decoded_path = os.path.join(OUTPUT_FOLDER, "decoded_secret.png")
        stego_img.save(stego_path)

        decrypted_key = decrypt(encrypted_key_input.strip(), AES_PASSWORD)
        data = list(map(int, decrypted_key.split(',')))

        if len(data) != 8:
            return jsonify({'success': False, 'error': 'Decrypted key must contain exactly 8 integers.'}), 400

        size = data[:4]
        level = data[4]
        encode_time = data[5]
        expiry_seconds = data[6]
        x = data[7]

        current_time = int(time.time())
        if current_time - encode_time > expiry_seconds:
            log_event("IMAGE_DECODE_EXPIRED", f"Stego: {stego_img.filename}, Expired by {current_time - encode_time - expiry_seconds}s")
            return jsonify({'success': False, 'error': 'Time limit exceeded'}), 400

        start_decode = time.time()
        image_in_image2.DECode_lsb(stego_path, decoded_path, size, level, x)
        end_decode = time.time()
        decode_time = round(end_decode - start_decode, 4)

        log_event("IMAGE_DECODE_SUCCESS", f"Stego: {stego_img.filename}, Level: {level}, Decode Time: {decode_time}s")
        return jsonify({
            "success": True,
            "decoded_image_url": "/api/download/decoded_secret.png",
            "decode_time": decode_time
        })
    except Exception as e:
        log_event("IMAGE_DECODE_FAILED", f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio-in-image/encode', methods=['POST'])
def audio_in_image_encode():
    try:
        audio_file = request.files.get("audio")
        image_file = request.files.get("cover_image")
        expiry_str = request.form.get("expiry_time", "").strip()

        if not audio_file or not image_file:
            return jsonify({'success': False, 'error': 'Audio and cover image are required.'}), 400

        try:
            expiry_seconds = int(expiry_str) if expiry_str else None
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid expiry time format.'}), 400
            
        if expiry_seconds is None:
            return jsonify({'success': False, 'error': 'Expiry time is required.'}), 400

        audio_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
        audio_file.save(audio_path)
        image_file.save(image_path)

        output_image_path = os.path.join(OUTPUT_FOLDER, "audio_stego.png")

        start_time = time.time()
        key, sample_rate = Start_Encode(audio_path, image_path, expiry_seconds, output_image_path)
        end_time = time.time()
        embed_time = round(end_time - start_time, 4)

        key_used = encrypt(f"{key}|{sample_rate}", AES_PASSWORD)
        log_event("AUDIO_ENCODE", f"Audio: {audio_file.filename}, Image: {image_file.filename}, Expiry: {expiry_seconds}s")
        return jsonify({
            "success": True,
            "encoded_image_url": "/api/download/audio_stego.png",
            "key": key_used,
            "embed_time": embed_time
        })
    except Exception as e:
        log_event("AUDIO_ENCODE_FAILED", f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio-in-image/decode', methods=['POST'])
def audio_in_image_decode():
    try:
        stego_image = request.files.get("stego_image")
        encrypted_key_str = request.form.get("secret_key", "").strip()

        if not stego_image or not encrypted_key_str:
            return jsonify({'success': False, 'error': 'Stego image and secret key are required.'}), 400

        try:
            decrypted = decrypt(encrypted_key_str, AES_PASSWORD)
            key_str, sample_rate_str = decrypted.split("|")
            key = int(key_str)
            sample_rate = int(sample_rate_str)
        except Exception as e:
            log_event("AUDIO_DECODE_KEY_ERROR", f"Invalid key or decryption failed: {e}")
            return jsonify({'success': False, 'error': 'Invalid or corrupted key'}), 400

        image_path = os.path.join(UPLOAD_FOLDER, stego_image.filename)
        stego_image.save(image_path)

        decoded_audio_output = os.path.join(OUTPUT_FOLDER, "decoded_audio.wav")

        start_time = time.time()
        Start_Decode(image_path, key, sample_rate, decoded_audio_output)
        end_time = time.time()
        decode_time = round(end_time - start_time, 4)

        log_event("AUDIO_DECODE_SUCCESS", f"Stego: {stego_image.filename}, Decode Time: {decode_time}s")
        return jsonify({
            "success": True,
            "decoded_audio_url": "/api/download/decoded_audio.wav",
            "decode_time": decode_time
        })
    except Exception as e:
        log_event("AUDIO_DECODE_FAILED", f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/text-in-text-zwc/encode', methods=['POST'])
def text_in_text_zwc_encode():
    try:
        cover_file = request.files.get("cover_text")
        secret_file = request.files.get("secret_file")
        expiry = request.form.get("expiry")

        if not cover_file or not secret_file or not expiry:
            return jsonify({'success': False, 'error': 'Cover text, secret file, and expiry are required.'}), 400

        expiry = int(expiry)
        cover_path = os.path.join(UPLOAD_FOLDER, cover_file.filename)
        secret_path = os.path.join(UPLOAD_FOLDER, secret_file.filename)

        cover_file.save(cover_path)
        secret_file.save(secret_path)

        start_time = time.time()
        with open(secret_path, "r", encoding="utf-8") as sfile:
            secret_message = sfile.read()

        output_file = os.path.join(OUTPUT_FOLDER, "stego_text.txt")
        encryption_key = text_in_text_zwc.encode_stego_file(
            input_file=cover_path,
            secret_message=secret_message,
            output_file=output_file,
            expiry_seconds=expiry
        )
        end_time = time.time()
        embed_time = round(end_time - start_time, 4)

        return jsonify({
            "success": True,
            "encoded_file_url": "/api/download/stego_text.txt",
            "encryption_key": encryption_key,
            "expiry": expiry,
            "embed_time": embed_time
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/text-in-text-zwc/decode', methods=['POST'])
def text_in_text_zwc_decode():
    try:
        stego_file = request.files.get("stego_file")
        user_key = request.form.get("secret_key")

        if not stego_file or not user_key:
            return jsonify({'success': False, 'error': 'Stego file and secret key are required.'}), 400

        stego_path = os.path.join(UPLOAD_FOLDER, stego_file.filename)
        stego_file.save(stego_path)
        output_file = os.path.join(OUTPUT_FOLDER, "decoded_message.txt")

        text_in_text_zwc.decode_stego_file(
            stego_file=stego_path,
            output_file=output_file,
            user_key=user_key
        )
        
        return jsonify({
            "success": True,
            "decoded_file_url": "/api/download/decoded_message.txt"
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/text-in-text-caesar/encode', methods=['POST'])
def text_in_text_caesar_encode():
    try:
        secret_file = request.files.get("secret_file")
        expiry = request.form.get("expiry")

        if not secret_file or not expiry:
            return jsonify({'success': False, 'error': 'Secret file and expiry are required.'}), 400

        expiry = int(expiry)
        secret_path = os.path.join(UPLOAD_FOLDER, secret_file.filename)
        secret_file.save(secret_path)

        output_file = os.path.join(OUTPUT_FOLDER, "stego_text_caecip.txt")
        start_time = time.time()
        encryption_key = text_in_text_caecip.encrypt(
            secret_file=secret_path,
            output_file=output_file,
            expiry_seconds=expiry
        )
        end_time = time.time()
        embed_time = round(end_time - start_time, 4)

        return jsonify({
            "success": True,
            "encoded_file_url": "/api/download/stego_text_caecip.txt",
            "encryption_key": encryption_key,
            "expiry": expiry,
            "embed_time": embed_time
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/text-in-text-caesar/decode', methods=['POST'])
def text_in_text_caesar_decode():
    try:
        stego_file = request.files.get("stego_file")
        user_key = request.form.get("secret_key")

        if not stego_file or not user_key:
            return jsonify({'success': False, 'error': 'Stego file and secret key are required.'}), 400

        stego_path = os.path.join(UPLOAD_FOLDER, stego_file.filename)
        stego_file.save(stego_path)

        output_file = os.path.join(OUTPUT_FOLDER, "decoded_message_caecip.txt")

        success, message = text_in_text_caecip.decrypt(
            secret_file=stego_path,
            output_file=output_file,
            user_key=user_key
        )

        if success:
            return jsonify({
                "success": True,
                "decoded_file_url": "/api/download/decoded_message_caecip.txt"
            })
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/evaluate/image-in-image', methods=['POST'])
def evaluate_image_in_image():
    try:
        original_image = request.files.get("original_image")
        stego_image = request.files.get("stego_image")
        if not original_image or not stego_image:
            return jsonify({'success': False, 'error': 'Both original and stego images are required.'}), 400
            
        original_path = os.path.join(UPLOAD_FOLDER, original_image.filename)
        stego_path = os.path.join(UPLOAD_FOLDER, stego_image.filename)
        original_image.save(original_path)
        stego_image.save(stego_path)
        
        psnr_value = image_in_image2.calculate_psnr_im_im(original_path, stego_path)
        hamming_value = image_in_image2.hamming_distance(original_path, stego_path)
        log_event("EVALUATE_AUDIO_IMAGE", f"Original: {original_image.filename}, Stego: {stego_image.filename}, PSNR: {psnr_value}, Hamming: {hamming_value}")
        
        return jsonify({
            "success": True,
            "psnr": psnr_value,
            "hamming": hamming_value
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/evaluate/text-in-image', methods=['POST'])
def evaluate_text_in_image():
    try:
        original_image = request.files.get("original_image")
        stego_image = request.files.get("stego_image")
        if not original_image or not stego_image:
            return jsonify({'success': False, 'error': 'Both original and stego images are required.'}), 400
            
        original_path = os.path.join(UPLOAD_FOLDER, original_image.filename)
        stego_path = os.path.join(UPLOAD_FOLDER, stego_image.filename)
        original_image.save(original_path)
        stego_image.save(stego_path)
        
        metrics = text_in_image.evaluate_steganography(original_path, stego_path)
        
        return jsonify({
            "success": True,
            "psnr": metrics.get("psnr"),
            "ssim": metrics.get("ssim"),
            "hamming": metrics.get("hamming")
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
