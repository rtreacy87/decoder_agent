"""
CTF Decoder Agent - Iterative decoding for nested encodings.

This package provides an intelligent agent for decoding nested encodings
commonly found in Capture The Flag (CTF) challenges.
"""

from .agent import DecoderAgent, iterative_decode
from .state import DecoderState
from .decoders import decode_base64, decode_hex, decode_rot13, decode_url
from .analysis import (
    analyze_encoding_characteristics,
    validate_decoded_result,
    print_analysis
)

__version__ = "0.1.0"
__all__ = [
    "DecoderAgent",
    "iterative_decode",
    "DecoderState",
    "decode_base64",
    "decode_hex",
    "decode_rot13",
    "decode_url",
    "analyze_encoding_characteristics",
    "validate_decoded_result",
    "print_analysis",
]
