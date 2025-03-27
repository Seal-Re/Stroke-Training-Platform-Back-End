from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base58

def check(formatted_ciphertext):
    key = b'Stroke-Training!'
    
    encoded_ciphertext_str = formatted_ciphertext.replace('-', '')
    encoded_ciphertext = encoded_ciphertext_str.encode()
    ciphertext = base58.b58decode(encoded_ciphertext)
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = cipher.decrypt(ciphertext)
    unpadded_data = unpad(decrypted_data, AES.block_size)
    decrypted_str = unpadded_data.decode()
    if decrypted_str.endswith("S"):
        return True 
    return False