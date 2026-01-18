"""
Text analysis and validation functions for the decoder agent.

This module provides comprehensive text analysis capabilities to identify encoding
characteristics, detect likely encoding types, and validate decoding results. It
implements a registry-based validator pattern for extensible result validation.

Key Components:
    - TextAnalysis: Container class for analysis metrics
    - Analysis functions: Character set, entropy, printable ratio detection
    - Encoding identification: Heuristic-based confidence scoring
    - Validator registry: Extensible pattern validation system

Usage:
    # Analyze text characteristics
    analysis = analyze_encoding_characteristics("SGVsbG8gV29ybGQ=")
    print(f"Charset: {analysis.charset}, Entropy: {analysis.entropy:.2f}")
    
    # Identify likely encodings
    confidence = identify_likely_encoding(analysis)
    print(f"Base64 confidence: {confidence['base64']}")
    
    # Validate decoded results
    result = validate_decoded_result(original="encoded", decoded="plain text")
    print(f"Status: {result['status']}, Confidence: {result['confidence']}")

Design Patterns:
    - Registry Pattern: Validators are registered with @register_validator
    - Strategy Pattern: Multiple validation strategies applied in priority order
    - Null Object Pattern: Default validator ensures result always returned

Dependencies:
    - math: Shannon entropy calculation
    - string: Printable character set
    - re: Pattern matching for flags, URLs, hashes
    - collections.Counter: Character frequency analysis

Author: Decoder Agent
"""

import math
import string
import re
import logging
from collections import Counter
from typing import Optional, Dict
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS: Analysis Thresholds
# ============================================================================

# Entropy thresholds (bits per character)
ENTROPY_HIGH_THRESHOLD = 5.5  # Above this indicates likely encoded/random
ENTROPY_LOW_THRESHOLD = 4.5   # Below this indicates natural language
ENTROPY_NATURAL_LANGUAGE = 4.1  # Typical English text

# Printable ratio thresholds
PRINTABLE_RATIO_HIGH = 0.95  # High confidence in readable text
PRINTABLE_RATIO_LOW = 0.80   # Low threshold for partial readability

# Text preview length for logging
TEXT_PREVIEW_LENGTH = 60

# Hash lengths
MD5_LENGTH = 32
SHA1_LENGTH = 40
SHA256_LENGTH = 64

# ============================================================================
# CONSTANTS: Character Sets
# ============================================================================

HEX_CHARS = '0123456789abcdefABCDEF'
BASE64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='

# ============================================================================
# CONSTANTS: Validator Confidence Scores
# ============================================================================

CONFIDENCE_FLAG_DETECTED = 0.99
CONFIDENCE_URL_DETECTED = 0.85
CONFIDENCE_HASH_DETECTED = 0.80
CONFIDENCE_NATURAL_LANGUAGE = 0.90
CONFIDENCE_STILL_ENCODED = 0.60
CONFIDENCE_IMPROVED_READABILITY = 0.50
CONFIDENCE_AMBIGUOUS = 0.45
CONFIDENCE_NO_CHANGE = 0.0

# ============================================================================
# CONSTANTS: Encoding Detection Confidence
# ============================================================================

CONFIDENCE_BASE64_CHARSET = 0.85
CONFIDENCE_BASE64_WITH_PADDING = 0.95
CONFIDENCE_BASE64_LENGTH_MATCH = 0.6

CONFIDENCE_HEX_CHARSET = 0.90
CONFIDENCE_HEX_EVEN_LENGTH = 0.95

CONFIDENCE_ROT13_ALPHABETIC = 0.70
CONFIDENCE_URL_PERCENT_ENCODING = 0.90

# ============================================================================
# CONSTANTS: Regex Patterns (Pre-compiled for performance)
# ============================================================================

# Flag patterns for CTF competitions
FLAG_PATTERNS = [
    re.compile(r'flag\{[^\}]+\}', re.IGNORECASE),
    re.compile(r'HTB\{[^\}]+\}', re.IGNORECASE),
    re.compile(r'CTF\{[^\}]+\}', re.IGNORECASE),
    re.compile(r'picoCTF\{[^\}]+\}', re.IGNORECASE),
    re.compile(r'FLAG\{[^\}]+\}', re.IGNORECASE),
    re.compile(r'FLG\{[^\}]+\}', re.IGNORECASE),
]

# URL pattern
URL_PATTERN = re.compile(r'https?://[^\s]+', re.IGNORECASE)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TextAnalysis:
    """
    Container for comprehensive text analysis results.
    
    This class encapsulates all metrics computed during text analysis,
    providing a single object that can be passed through the decoding pipeline.
    
    Attributes:
        text: The analyzed text
        length: Number of characters
        charset: Detected character set type
        padding: Whether text has Base64-style padding
        entropy: Shannon entropy in bits per character
        printable_ratio: Ratio of printable ASCII characters (0.0-1.0)
        contains_url: Whether URL patterns detected
        contains_flag: Whether CTF flag patterns detected
        hash_type: Detected hash type or None
    """
    text: str
    length: int
    charset: str
    padding: bool
    entropy: float
    printable_ratio: float
    contains_url: bool
    contains_flag: bool
    hash_type: Optional[str]
    
    @classmethod
    def from_text(cls, text: str) -> "TextAnalysis":
        """
        Factory method to create TextAnalysis from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            TextAnalysis instance with all metrics computed
        """
        return cls(
            text=text,
            length=len(text),
            charset=identify_charset(text),
            padding=has_padding(text),
            entropy=calculate_entropy(text),
            printable_ratio=calculate_printable_ratio(text),
            contains_url=contains_url(text),
            contains_flag=contains_flag(text),
            hash_type=looks_like_hash(text)
        )


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================


def identify_charset(text: str) -> str:
    """
    Identify the character set of the text.
    
    This function performs early-exit checks in order of specificity to
    determine what type of characters make up the text. Useful for
    selecting appropriate decoders.
    
    Args:
        text: The text to analyze
        
    Returns:
        Character set type: "hex", "base64", "alphabetic", "printable", 
        "binary", or "empty"
        
    Examples:
        >>> identify_charset("48656c6c6f")
        "hex"
        >>> identify_charset("SGVsbG8=")
        "base64"
        >>> identify_charset("Hello World")
        "alphabetic"
    """
    if not text:
        logger.debug("Empty text detected")
        return "empty"
    
    # Check for hex (0-9a-fA-F only)
    # Strip spaces to handle formatted hex (e.g., "48 65 6c 6c 6f")
    if all(c in HEX_CHARS for c in text.replace(' ', '')):
        logger.debug(f"Hex charset detected (length={len(text)})")
        return "hex"
    
    # Check for base64 (A-Za-z0-9+/= only)
    if all(c in BASE64_CHARS for c in text):
        logger.debug(f"Base64 charset detected (length={len(text)})")
        return "base64"
    
    # Check if all printable
    if all(c in string.printable for c in text):
        # Check if mostly alphabetic (>70% letters)
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count / len(text) > 0.7:
            logger.debug(f"Alphabetic text detected ({alpha_count}/{len(text)} letters)")
            return "alphabetic"
        logger.debug("Printable text detected (mixed characters)")
        return "printable"
    
    # Contains non-printable characters
    logger.debug("Binary data detected (non-printable characters)")
    return "binary"


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of text.
    
    Shannon entropy measures the randomness or information density of text.
    Higher entropy indicates more random/encoded text, while lower entropy
    suggests natural language or patterns.
    
    Typical values:
        - Natural English: ~4.1-4.5 bits/char
        - Random/encrypted: ~7-8 bits/char
        - Repeated patterns: <3 bits/char
    
    Args:
        text: The text to analyze
        
    Returns:
        Shannon entropy value in bits per character (typically 0-8)
        
    Note:
        Returns 0.0 for empty strings (by convention).
    """
    if not text:
        return 0.0
    
    # Count character frequencies
    counts = Counter(text)
    total = len(text)
    
    # Calculate entropy: H = -Σ(p * log₂(p))
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    
    logger.debug(f"Calculated entropy: {entropy:.2f} bits/char (length={total})")
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
    
    Uses pre-compiled regex for performance. Detects http:// and https://
    URLs with common patterns.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if URL-like patterns are found, False otherwise
    """
    has_url = bool(URL_PATTERN.search(text))
    if has_url:
        logger.debug("URL pattern detected in text")
    return has_url


def contains_flag(text: str) -> bool:
    """
    Check for common CTF flag formats.
    
    Uses pre-compiled regex patterns to detect common CTF flag formats
    including flag{}, HTB{}, CTF{}, picoCTF{}, FLAG{}, and FLG{}.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if any flag pattern is found, False otherwise
        
    Note:
        Patterns are case-insensitive. Returns on first match for efficiency.
    """
    for pattern in FLAG_PATTERNS:
        if pattern.search(text):
            logger.debug(f"Flag pattern detected: {pattern.pattern}")
            return True
    return False


def looks_like_hash(text: str) -> Optional[str]:
    """
    Identify if text looks like a cryptographic hash.
    
    Checks for common hash formats based on length and hex character composition.
    
    Args:
        text: The text to analyze
        
    Returns:
        Hash type string ("MD5", "SHA1", "SHA256") or None if not a hash
        
    Note:
        Requires exact length match and all hex characters. No false positives
        unless text happens to be exactly 32, 40, or 64 hex characters.
    """
    text = text.strip()
    
    # Check if all characters are hex
    if not all(c in HEX_CHARS for c in text):
        return None
    
    # MD5: 32 hex characters
    if len(text) == MD5_LENGTH:
        logger.debug("MD5 hash pattern detected")
        return "MD5"
    
    # SHA1: 40 hex characters
    if len(text) == SHA1_LENGTH:
        logger.debug("SHA1 hash pattern detected")
        return "SHA1"
    
    # SHA256: 64 hex characters
    if len(text) == SHA256_LENGTH:
        logger.debug("SHA256 hash pattern detected")
        return "SHA256"
    
    return None


def analyze_encoding_characteristics(text: str) -> TextAnalysis:
    """
    Perform comprehensive analysis of text characteristics.
    
    This is the main entry point for text analysis. It computes all metrics
    and returns a TextAnalysis object containing the results.
    
    Args:
        text: The text to analyze
        
    Returns:
        TextAnalysis object with all metrics computed
        
    Example:
        >>> analysis = analyze_encoding_characteristics("SGVsbG8=")
        >>> print(f"Type: {analysis.charset}, Entropy: {analysis.entropy:.2f}")
        Type: base64, Entropy: 2.75
    """
    logger.debug(f"Analyzing text characteristics (length={len(text)})")
    return TextAnalysis.from_text(text)


# ============================================================================
# ENCODING IDENTIFICATION
# ============================================================================


def identify_likely_encoding(analysis: TextAnalysis) -> Dict[str, float]:
    """
    Identify likely encodings based on analysis metrics.
    
    Returns confidence scores for each encoding type based on heuristic
    analysis of text characteristics. Higher scores indicate higher confidence
    that a particular decoder should be applied.
    
    Args:
        analysis: TextAnalysis object with computed metrics
        
    Returns:
        Dictionary mapping encoding_type -> confidence score (0.0-1.0)
        Keys: "base64", "hex", "rot13", "url"
        
    Example:
        >>> analysis = analyze_encoding_characteristics("SGVsbG8=")
        >>> scores = identify_likely_encoding(analysis)
        >>> print(scores["base64"])
        0.95
    """
    confidence = {
        "base64": 0.0,
        "hex": 0.0,
        "rot13": 0.0,
        "url": 0.0,
    }
    
    # Base64 detection
    if analysis.charset == "base64":
        confidence["base64"] = CONFIDENCE_BASE64_CHARSET
        if analysis.padding:
            confidence["base64"] = CONFIDENCE_BASE64_WITH_PADDING
            logger.debug("Base64 detected: charset match with padding")
        else:
            logger.debug("Base64 detected: charset match without padding")
    elif analysis.length % 4 == 0 and analysis.charset in ["printable", "base64"]:
        confidence["base64"] = CONFIDENCE_BASE64_LENGTH_MATCH
        logger.debug("Base64 detected: length divisible by 4")
    
    # Hex detection
    if analysis.charset == "hex":
        confidence["hex"] = CONFIDENCE_HEX_CHARSET
        if analysis.length % 2 == 0:
            confidence["hex"] = CONFIDENCE_HEX_EVEN_LENGTH
            logger.debug("Hex detected: charset match with even length")
        else:
            logger.debug("Hex detected: charset match with odd length")
    
    # ROT13 detection (only applies to alphabetic text)
    if analysis.charset == "alphabetic":
        confidence["rot13"] = CONFIDENCE_ROT13_ALPHABETIC
        logger.debug("ROT13 candidate: alphabetic text detected")
    
    # URL encoding detection (presence of % indicates URL encoding)
    if '%' in analysis.text:
        confidence["url"] = CONFIDENCE_URL_PERCENT_ENCODING
        logger.debug("URL encoding detected: percent signs present")
    
    return confidence

# ============================================================================
# VALIDATOR REGISTRY PATTERN
# ============================================================================

# Registry of validators in priority order
# Validators are checked sequentially; first non-None result wins
VALIDATION_REGISTRY = []


def register_validator(func):
    """
    Decorator to register a validator function in the validation registry.
    
    Validators are executed in registration order when validating decoded results.
    Each validator should accept (original: str, analysis: TextAnalysis) and
    return either a validation dict or None.
    
    Args:
        func: Validator function to register
        
    Returns:
        The function unchanged (identity decorator)
        
    Example:
        @register_validator
        def my_validator(original: str, analysis: TextAnalysis) -> Optional[Dict]:
            if some_condition:
                return {"status": "COMPLETE", "reason": "...", "confidence": 0.9}
            return None
    """
    VALIDATION_REGISTRY.append(func)
    logger.debug(f"Registered validator: {func.__name__}")
    return func


# ============================================================================
# VALIDATORS (registered in priority order)
# ============================================================================
@register_validator
def _validator_no_change(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if decoding produced no change.
    
    Priority: 1 (highest)
    Confidence: 0.0 (failure indicator)
    
    If the decoded text is identical to the original, the decoder did nothing
    and we should mark this as a failed decode attempt.
    """
    if original == analysis.text:
        logger.info("Validator: No change after decoding (FAILED)")
        return {
            "status": "FAILED",
            "reason": "No change after decoding",
            "confidence": CONFIDENCE_NO_CHANGE
        }
    return None


@register_validator
def _validator_flag(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if flag format detected.
    
    Priority: 2
    Confidence: 0.99 (very high)
    
    CTF flags in standard format (flag{...}, HTB{...}, etc.) are strong
    indicators of successful decoding completion.
    """
    if analysis.contains_flag:
        logger.info("Validator: Flag format detected (COMPLETE)")
        return {
            "status": "COMPLETE",
            "reason": "Flag format detected",
            "confidence": CONFIDENCE_FLAG_DETECTED
        }
    return None


@register_validator
def _validator_url(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if URL detected.
    
    Priority: 3
    Confidence: 0.85 (high)
    
    URLs are common targets in encoding challenges and indicate
    likely successful decoding.
    """
    if analysis.contains_url:
        logger.info("Validator: URL detected (COMPLETE)")
        return {
            "status": "COMPLETE",
            "reason": "URL detected",
            "confidence": CONFIDENCE_URL_DETECTED
        }
    return None


@register_validator
def _validator_hash(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if hash format detected.
    
    Priority: 4
    Confidence: 0.80 (medium-high)
    
    Cryptographic hashes (MD5, SHA1, SHA256) indicate a meaningful result,
    though they may be intermediate steps in multi-stage challenges.
    """
    if analysis.hash_type:
        logger.info(f"Validator: {analysis.hash_type} hash detected (COMPLETE)")
        return {
            "status": "COMPLETE",
            "reason": f"{analysis.hash_type} hash detected",
            "confidence": CONFIDENCE_HASH_DETECTED
        }
    return None


@register_validator
def _validator_natural_language(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if text appears to be natural language.
    
    Priority: 5
    Confidence: 0.90 (high)
    
    Text with high printable ratio and low entropy (typical of English)
    strongly suggests successful decoding to readable plaintext.
    """
    if analysis.printable_ratio > PRINTABLE_RATIO_HIGH and analysis.entropy < ENTROPY_LOW_THRESHOLD:
        logger.info(
            f"Validator: Natural language detected "
            f"(printable={analysis.printable_ratio:.2f}, entropy={analysis.entropy:.2f}) (COMPLETE)"
        )
        return {
            "status": "COMPLETE",
            "reason": "Natural language detected (high printable ratio, low entropy)",
            "confidence": CONFIDENCE_NATURAL_LANGUAGE
        }
    return None


@register_validator
def _validator_still_encoded(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if text still appears encoded.
    
    Priority: 6
    Confidence: 0.60 (medium)
    
    Low printable ratio or high entropy suggests the text is still encoded
    and requires additional decoding passes.
    """
    if analysis.printable_ratio < PRINTABLE_RATIO_LOW or analysis.entropy > ENTROPY_HIGH_THRESHOLD:
        logger.info(
            f"Validator: Still appears encoded "
            f"(printable={analysis.printable_ratio:.2f}, entropy={analysis.entropy:.2f}) (PARTIAL)"
        )
        return {
            "status": "PARTIAL",
            "reason": f"Still appears encoded (printable={analysis.printable_ratio:.2f}, entropy={analysis.entropy:.2f})",
            "confidence": CONFIDENCE_STILL_ENCODED
        }
    return None


@register_validator
def _validator_improved_readability(original: str, analysis: TextAnalysis) -> Optional[Dict]:
    """
    Validator: Check if readability improved but still ambiguous.
    
    Priority: 7
    Confidence: 0.50 (medium-low)
    
    Reasonable printable ratio but not clearly natural language. May need
    additional processing or could be the final result.
    """
    if analysis.printable_ratio > PRINTABLE_RATIO_LOW:
        logger.info(
            f"Validator: Improved readability but ambiguous "
            f"(printable={analysis.printable_ratio:.2f}) (PARTIAL)"
        )
        return {
            "status": "PARTIAL",
            "reason": "Improved readability but still ambiguous",
            "confidence": CONFIDENCE_IMPROVED_READABILITY
        }
    return None


@register_validator
def _validator_default(original: str, analysis: TextAnalysis) -> Dict:
    """
    Fallback validator (Null Object Pattern).
    
    Priority: 8 (lowest, always matches)
    Confidence: 0.45 (low)
    
    This validator always returns a result, ensuring validate_decoded_result()
    never fails to produce output. Acts as the null object in the pattern.
    """
    logger.info("Validator: Using default (ambiguous result) (PARTIAL)")
    return {
        "status": "PARTIAL",
        "reason": "Ambiguous result",
        "confidence": CONFIDENCE_AMBIGUOUS
    }


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_decoded_result(original: str, decoded: str) -> Dict:
    """
    Comprehensive validation of a decoded result using registry pattern.
    
    This function analyzes the decoded text and runs it through registered
    validators in priority order. The first validator that returns a non-None
    result determines the validation outcome.
    
    Validators check for:
        1. No change (failure)
        2. Flag patterns (complete)
        3. URLs (complete)
        4. Hash patterns (complete)
        5. Natural language (complete)
        6. Still encoded (partial)
        7. Improved readability (partial)
        8. Default ambiguous (partial)
    
    Args:
        original: The original encoded text
        decoded: The decoded text to validate
        
    Returns:
        Dictionary with validation results:
        {
            "status": "COMPLETE" | "PARTIAL" | "FAILED",
            "reason": str (human-readable explanation),
            "confidence": float (0.0-1.0)
        }
        
    Example:
        >>> result = validate_decoded_result("ZmxhZ3t0ZXN0fQ==", "flag{test}")
        >>> print(result["status"])
        COMPLETE
        >>> print(result["confidence"])
        0.99
    """
    # Analyze the decoded result
    logger.debug(f"Validating decode: original length={len(original)}, decoded length={len(decoded)}")
    analysis = analyze_encoding_characteristics(decoded)
    
    # Run validators in priority order
    for validator in VALIDATION_REGISTRY:
        result = validator(original, analysis)
        if result is not None:
            logger.debug(f"Validator {validator.__name__} returned result: {result['status']}")
            return result
    
    # Fallback (should rarely reach here due to _validator_default)
    logger.warning("No validator matched; using default fallback")
    return _validator_default(original, analysis)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_analysis(text: str) -> None:
    """
    Print a formatted analysis of text.
    
    Useful for debugging and manual inspection of text characteristics.
    Displays all metrics in a readable table format.
    
    Args:
        text: The text to analyze and display
        
    Example:
        >>> print_analysis("SGVsbG8gV29ybGQh")
        ======================================================================
        TEXT ANALYSIS
        ======================================================================
        Text: SGVsbG8gV29ybGQh
        Length: 16 characters
        Character Set: base64
        Printable Ratio: 100.00%
        Entropy: 3.12 bits/char
        Has Padding (=): False
        Contains URL: False
        Contains Flag: False
        Hash Type: None
        ======================================================================
    """
    analysis = analyze_encoding_characteristics(text)
    
    print("\n" + "=" * 70)
    print("TEXT ANALYSIS")
    print("=" * 70)
    preview = text[:TEXT_PREVIEW_LENGTH] + ('...' if len(text) > TEXT_PREVIEW_LENGTH else '')
    print(f"Text: {preview}")
    print(f"Length: {analysis.length} characters")
    print(f"Character Set: {analysis.charset}")
    print(f"Printable Ratio: {analysis.printable_ratio:.2%}")
    print(f"Entropy: {analysis.entropy:.2f} bits/char")
    print(f"Has Padding (=): {analysis.padding}")
    print(f"Contains URL: {analysis.contains_url}")
    print(f"Contains Flag: {analysis.contains_flag}")
    print(f"Hash Type: {analysis.hash_type or 'None'}")
    print("=" * 70 + "\n")
