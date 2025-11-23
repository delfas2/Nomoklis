from django.conf import settings
from cryptography.fernet import Fernet

# It's good practice to instantiate Fernet only once and reuse it
fernet = Fernet(settings.CHAT_ENCRYPTION_KEY)

def encode_room_name(user_id1, user_id2):
    """Encrypts two user IDs into a URL-safe string."""
    ids = sorted([user_id1, user_id2])
    ids_string = f"{ids[0]}_{ids[1]}"
    return fernet.encrypt(ids_string.encode()).decode()

def decode_room_name(encrypted_room_name):
    """Decrypts a URL-safe string and returns the original room name string."""
    try:
        decrypted_ids = fernet.decrypt(encrypted_room_name.encode()).decode()
        return f"chat_{decrypted_ids}"
    except Exception: # Catching a broad exception as fernet can raise multiple
        return None

def encrypt_id(id_value):
    """Encrypts an integer ID into a URL-safe string."""
    return fernet.encrypt(str(id_value).encode()).decode()

def decrypt_id(encrypted_id):
    """Decrypts a URL-safe string and returns the original integer ID."""
    try:
        decrypted_id = fernet.decrypt(encrypted_id.encode()).decode()
        return int(decrypted_id)
    except Exception:
        return None
