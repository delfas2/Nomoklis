"""
File upload validators for security.
Ensures only safe file types and sizes are uploaded.
"""
from django.core.exceptions import ValidationError
import os

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
MAX_FILE_SIZE_MB = 10  # 10 MB

def validate_image_extension(value):
    """
    Validate that uploaded file is an allowed image type.
    """
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Netinkamas failo tipas. Leidžiami: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        )

def validate_document_extension(value):
    """
    Validate that uploaded file is an allowed document type.
    """
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f'Netinkamas failo tipas. Leidžiami: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
        )

def validate_file_size(value):
    """
    Validate that uploaded file size is within limits.
    """
    filesize = value.size
    max_size = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    if filesize > max_size:
        raise ValidationError(
            f'Failas per didelis. Maksimalus dydis: {MAX_FILE_SIZE_MB} MB'
        )
