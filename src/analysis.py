"""
Text analysis and validation functions for the decoder agent.

This module provides functions to analyze encoded text characteristics,
identify likely encodings, and validate decoding results.
"""

import math
import string
import re
from collections import Counter
from typing import Optional, Dict


class TextAnalysis:
    """Container for text analysis results."""
    
    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.charset = identify_charset(text)
        self.padding = has_padding(text)
        self.entropy = calculate_entropy(text)
        self.printable_ratio = calculate_printable_ratio(text)
        self.contains_url = contains_url(text)
        self.contains_flag = contains_flag(text)
        self.hash_type = looks_like_hash(text)


def identify_charset(text: str) -> str:
    """
    Identify the character set of the text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Character set type: "hex", "base64", "alphanumeric", "printable", or "binary"
    """
    if not text:
        return "empty"
    
    # Check for hex (0-9a-fA-F only)
    if all(c in '0123456789abcdefABCDEF' for c in text.replace(' ', '')):
        return "hex"
    
    # Check for base64 (A-Za-z0-9+/= only)
    if all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in text):
        return "base64"
    
    # Check if all printable
    if all(c in string.printable for c in text):
        # Check if mostly alphabetic
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count / len(text) > 0.7:
            return "alphabetic"
        return "printable"
    
    # Contains non-printable characters
    return "binary"


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of text.
    
    Higher entropy indicates more random/encoded text.
    Natural English text typically has entropy around 4.1-4.5 bits/char.
    
    Args:
        text: The text to analyze
        
    Returns:
        Shannon entropy value (bits per character)
    """
    if not text:
        return 0.0
    
    # Count character frequencies
    counts = Counter(text)
    total = len(text)
    
    # Calculate entropy
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    
    return entropy


def calculate_printable_ratio(text: str) -> float:
    """
    Calculate the ratio of printable ASCII characters.
    
    Args:
        text: The text to analyze
        
    Returns:
        Ratio of printable characters (0.0 to 1.0)
    """
    if not text:
        return 0.0
    
    printable_count = sum(1 for c in text if c in string.printable)
    return printable_count / len(text)


def has_padding(text: str) -> bool:
    """
    Check if text has Base64-style padding.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if text ends with = or ==
    """
    return text.rstrip().endswith('=') or text.rstrip().endswith('==')


def contains_url(text: str) -> bool:
    """
    Check if text contains URL patterns.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if URL-like patterns are found
    """
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, text, re.IGNORECASE))


def contains_flag(text: str) -> bool:
    """
    Check for common CTF flag formats.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if a flag pattern is found
    """
    flag_patterns = [
        r'flag\{[^\}]+\}',
        r'HTB\{[^\}]+\}',
        r'CTF\{[^\}]+\}',
        r'picoCTF\{[^\}]+\}',
        r'FLAG\{[^\}]+\}',
        r'FLG\{[^\}]+\}',
    ]
    
    for pattern in flag_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def looks_like_hash(text: str) -> Optional[str]:
    """
    Identify if text looks like a cryptographic hash.
    
    Args:
        text: The text to analyze
        
    Returns:
        Hash type (MD5, SHA1, SHA256) or None
    """
    text = text.strip()
    
    # MD5: 32 hex characters
    if len(text) == 32 and all(c in '0123456789abcdefABCDEF' for c in text):
        return "MD5"
    
    # SHA1: 40 hex characters
    if len(text) == 40 and all(c in '0123456789abcdefABCDEF' for c in text):
        return "SHA1"
    
    # SHA256: 64 hex characters
    if len(text) == 64 and all(c in '0123456789abcdefABCDEF' for c in text):
        return "SHA256"
    
    return None


def analyze_encoding_characteristics(text: str) -> TextAnalysis:
    """
    Perform comprehensive analysis of text characteristics.
    
    Args:
        text: The text to analyze
        
    Returns:
        TextAnalysis object with all metrics
    """
    return TextAnalysis(text)


def identify_likely_encoding(analysis: TextAnalysis) -> Dict[str, float]:
    """
    Identify likely encodings based on analysis.
    
    Returns confidence scores for each encoding type.
    
    Args:
        analysis: TextAnalysis object with computed metrics
        
    Returns:
        Dictionary of encoding_type -> confidence score (0.0-1.0)
    """
    confidence = {
        "base64": 0.0,
        "hex": 0.0,
        "rot13": 0.0,
        "url": 0.0,
    }
    
    # Base64 detection
    if analysis.charset == "base64":
        confidence["base64"] = 0.85
        if analysis.padding:
            confidence["base64"] = 0.95
    elif analysis.length % 4 == 0 and analysis.charset in ["printable", "base64"]:
        confidence["base64"] = 0.6
    
    # Hex detection
    if analysis.charset == "hex":
        confidence["hex"] = 0.90
        if analysis.length % 2 == 0:
            confidence["hex"] = 0.95
    
    # ROT13 detection
    if analysis.charset == "alphabetic":
        confidence["rot13"] = 0.70
    
    # URL detection
    if '%' in analysis.text:
        confidence["url"] = 0.90
    
    return confidence
    
# Registry of validators in priority order
# Use a list to preserve priority (insertion) order and store callables
VALIDATION_REGISTRY = []

def register_validator(func):
    """Decorator to register a validator function."""
    VALIDATION_REGISTRY.append(func)
    return func

# Keep backward-compatible alias for the misspelled name
# resigter_validator = register_validator

# Validation registry pattern
@register_validator
def _validator_no_change(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if decoding produced no change."""
    if original == analysis.text:
        return {
            "status": "FAILED",
            "reason": "No change after decoding",
            "confidence": 0.0
        }
    return None

@register_validator
def _validator_flag(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if flag format detected."""
    if analysis.contains_flag:
        return {
            "status": "COMPLETE",
            "reason": "Flag format detected",
            "confidence": 0.99
        }
    return None

@register_validator
def _validator_url(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if URL detected."""
    if analysis.contains_url:
        return {
            "status": "COMPLETE",
            "reason": "URL detected",
            "confidence": 0.85
        }
    return None

@register_validator
def _validator_hash(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if hash format detected."""
    if analysis.hash_type:
        return {
            "status": "COMPLETE",
            "reason": f"{analysis.hash_type} hash detected",
            "confidence": 0.80
        }
    return None

@register_validator
def _validator_natural_language(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if text appears to be natural language."""
    if analysis.printable_ratio > 0.95 and analysis.entropy < 4.5:
        return {
            "status": "COMPLETE",
            "reason": "Natural language detected (high printable ratio, low entropy)",
            "confidence": 0.90
        }
    return None

@register_validator
def _validator_still_encoded(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if text still appears encoded."""
    if analysis.printable_ratio < 0.80 or analysis.entropy > 5.5:
        return {
            "status": "PARTIAL",
            "reason": f"Still appears encoded (printable={analysis.printable_ratio:.2f}, entropy={analysis.entropy:.2f})",
            "confidence": 0.60
        }
    return None

@register_validator
def _validator_improved_readability(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """Validator: Check if readability improved but still ambiguous."""
    if analysis.printable_ratio > 0.80:
        return {
            "status": "PARTIAL",
            "reason": "Improved readability but still ambiguous",
            "confidence": 0.50
        }
    return None

@register_validator
def _validator_default(original: str, analysis: TextAnalysis) -> Dict:
    """Fallback validator when no other rules match."""
    return {
        "status": "PARTIAL",
        "reason": "Ambiguous result",
        "confidence": 0.45
    }


def validate_decoded_result(original: str, decoded: str) -> Dict:
    """
    Comprehensive validation of a decoded result using a registry pattern.
    
    Validators are checked in priority order. The first validator that
    returns a non-None result is used.
    
    Args:
        original: The original encoded text
        decoded: The decoded text
        
    Returns:
        Dictionary with validation results:
        {
            "status": "COMPLETE" | "PARTIAL" | "FAILED",
            "reason": str,
            "confidence": float
        }
    """
    # Analyze the decoded result
    analysis = analyze_encoding_characteristics(decoded)
    
    # Run validators in priority order
    for validator in VALIDATION_REGISTRY:
        result = validator(original, analysis)
        if result is not None:
            return result
    
    # Fallback (should rarely reach here)
    return _validator_default(original, analysis)


def print_analysis(text: str) -> None:
    """
    Print a formatted analysis of text.
    
    Args:
        text: The text to analyze
    """
    analysis = analyze_encoding_characteristics(text)
    
    print("\n" + "=" * 70)
    print("TEXT ANALYSIS")
    print("=" * 70)
    print(f"Text: {text[:60]}{'...' if len(text) > 60 else ''}")
    print(f"Length: {analysis.length} characters")
    print(f"Character Set: {analysis.charset}")
    print(f"Printable Ratio: {analysis.printable_ratio:.2%}")
    print(f"Entropy: {analysis.entropy:.2f} bits/char")
    print(f"Has Padding (=): {analysis.padding}")
    print(f"Contains URL: {analysis.contains_url}")
    print(f"Contains Flag: {analysis.contains_flag}")
    print(f"Hash Type: {analysis.hash_type or 'None'}")
    print("=" * 70 + "\n")
