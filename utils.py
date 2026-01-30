"""
Utility functions for Social Media Platform
"""
import os
import imghdr
from datetime import datetime

def validate_image(stream):
    """Validate if file is an image"""
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

def get_file_extension(filename):
    """Get file extension"""
    return os.path.splitext(filename)[1].lower()

def format_datetime(value):
    """Format datetime for display"""
    if not value:
        return ""
    return value.strftime('%Y-%m-%d %H:%M:%S')
