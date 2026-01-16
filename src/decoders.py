"""
Decoder tools for various encoding formats.

This module provides functions to decode different encoding types commonly
found in CTF challenges: Base64, Hex, ROT13, and URL encoding.
"""

import base64
import binascii
from typing import Tuple, Optional


class DecoderError(Exception):
    """Raised when a decoder fails to decode text."""
    pass


def decode_base64(encoded_text: str) -> str:
    """
    Decode a Base64 encoded string.
    
    Args:
        encoded_text: The Base64 encoded string
        
    Returns:
        The decoded string
        
    Raises:
        DecoderError: If the text is not valid Base64
    """
    try:
        # Ensure the text is a string
        if isinstance(encoded_text, bytes):
            encoded_text = encoded_text.decode('utf-8')
        
        # Try to decode
        decoded = base64.b64decode(encoded_text)
        
        # Try to decode as UTF-8
        try:
            return decoded.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 fails, return as hex string
            return decoded.hex()
    
    except (ValueError, binascii.Error) as e:
        raise DecoderError(f"Failed to decode Base64: {str(e)}")


def decode_hex(encoded_text: str) -> str:
    """
    Decode a Hexadecimal encoded string.
    
    Args:
        encoded_text: The hexadecimal encoded string
        
    Returns:
        The decoded string
        
    Raises:
        DecoderError: If the text is not valid hexadecimal
    """
    try:
        # Remove whitespace
        encoded_text = encoded_text.replace(" ", "").replace("\n", "").replace("\t", "")
        
        # Check if valid hex
        if not all(c in '0123456789abcdefABCDEF' for c in encoded_text):
            raise DecoderError("Text contains non-hexadecimal characters")
        
        # Must be even length
        if len(encoded_text) % 2 != 0:
            raise DecoderError("Hexadecimal string has odd length")
        
        # Decode
        decoded = bytes.fromhex(encoded_text)
        
        # Try to decode as UTF-8
        try:
            return decoded.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 fails, return as base64
            return base64.b64encode(decoded).decode('utf-8')
    
    except DecoderError:
        raise
    except Exception as e:
        raise DecoderError(f"Failed to decode hexadecimal: {str(e)}")


def decode_rot13(encoded_text: str) -> str:
    """
    Decode a ROT13 encoded string.
    
    ROT13 is a simple letter substitution cipher that replaces a letter
    with the 13th letter after it in the alphabet.
    
    Args:
        encoded_text: The ROT13 encoded string
        
    Returns:
        The decoded string
        
    Raises:
        DecoderError: If the text cannot be decoded as ROT13
    """
    try:
        result = []
        for char in encoded_text:
            if 'a' <= char <= 'z':
                # Lowercase letters
                result.append(chr((ord(char) - ord('a') + 13) % 26 + ord('a')))
            elif 'A' <= char <= 'Z':
                # Uppercase letters
                result.append(chr((ord(char) - ord('A') + 13) % 26 + ord('A')))
            else:
                # Non-alphabetic characters remain unchanged
                result.append(char)
        
        return ''.join(result)
    
    except Exception as e:
        raise DecoderError(f"Failed to decode ROT13: {str(e)}")


def decode_url(encoded_text: str) -> str:
    """
    Decode a URL encoded (percent-encoded) string.
    
    Args:
        encoded_text: The URL encoded string
        
    Returns:
        The decoded string
        
    Raises:
        DecoderError: If the text is not valid URL encoding
    """
    try:
        from urllib.parse import unquote
        
        # Ensure the text is a string
        if isinstance(encoded_text, bytes):
            encoded_text = encoded_text.decode('utf-8')
        
        # Check if it looks like URL encoding
        if '%' not in encoded_text:
            raise DecoderError("Text does not appear to be URL encoded (no % found)")
        
        decoded = unquote(encoded_text)
        
        # Check if anything actually changed
        if decoded == encoded_text:
            raise DecoderError("URL decoding resulted in no change")
        
        return decoded
    
    except DecoderError:
        raise
    except Exception as e:
        raise DecoderError(f"Failed to decode URL encoding: {str(e)}")


def try_all_decoders(encoded_text: str) -> list:
    """
    Try all available decoders and return successful results.
    
    This is useful for testing which decoders might work on a given input.
    
    Args:
        encoded_text: The text to decode
        
    Returns:
        List of tuples: (decoder_name, decoded_result)
    """
    decoders = [
        ("base64", decode_base64),
        ("hex", decode_hex),
        ("rot13", decode_rot13),
        ("url", decode_url),
    ]
    
    results = []
    for name, decoder_func in decoders:
        try:
            result = decoder_func(encoded_text)
            if result != encoded_text:  # Only include if it actually changed
                results.append((name, result))
        except DecoderError:
            pass  # Skip decoders that fail
    
    return results
