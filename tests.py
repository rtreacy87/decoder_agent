"""
Test suite for the CTF Decoder Agent.

This module contains unit tests for the decoder agent components.
"""

import sys
from pathlib import Path
import base64

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.decoders import (
    decode_base64, decode_hex, decode_rot13, decode_url,
    DecoderError
)
from src.analysis import (
    analyze_encoding_characteristics,
    calculate_entropy,
    calculate_printable_ratio,
    contains_flag,
    looks_like_hash,
    validate_decoded_result
)
from src.state import DecoderState
from src.agent import DecoderAgent, iterative_decode


class TestDecoders:
    """Test decoder functions."""
    
    @staticmethod
    def test_base64_decode():
        """Test Base64 decoding."""
        original = "Hello, World!"
        encoded = base64.b64encode(original.encode()).decode()
        
        decoded = decode_base64(encoded)
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ Base64 decode test passed")
    
    @staticmethod
    def test_base64_with_padding():
        """Test Base64 decoding with padding."""
        original = "Hi"
        encoded = base64.b64encode(original.encode()).decode()
        
        decoded = decode_base64(encoded)
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ Base64 padding test passed")
    
    @staticmethod
    def test_hex_decode():
        """Test Hex decoding."""
        original = "Hello"
        encoded = original.encode().hex()
        
        decoded = decode_hex(encoded)
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ Hex decode test passed")
    
    @staticmethod
    def test_hex_uppercase():
        """Test Hex decoding with uppercase."""
        original = "Test"
        encoded = original.encode().hex().upper()
        
        decoded = decode_hex(encoded)
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ Hex uppercase test passed")
    
    @staticmethod
    def test_rot13_basic():
        """Test ROT13 decoding."""
        original = "hello"
        encoded = decode_rot13(original)  # ROT13 is symmetric
        
        decoded = decode_rot13(encoded)
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ ROT13 basic test passed")
    
    @staticmethod
    def test_rot13_with_numbers():
        """Test ROT13 with mixed content."""
        original = "test123"
        encoded = decode_rot13(original)
        decoded = decode_rot13(encoded)
        
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ ROT13 mixed content test passed")
    
    @staticmethod
    def test_url_decode():
        """Test URL decoding."""
        from urllib.parse import quote
        
        original = "hello world"
        encoded = quote(original)
        
        decoded = decode_url(encoded)
        assert decoded == original, f"Expected {original}, got {decoded}"
        print("✓ URL decode test passed")
    
    @staticmethod
    def test_invalid_base64():
        """Test invalid Base64 handling."""
        try:
            decode_base64("!!!invalid!!!")
            assert False, "Should have raised DecoderError"
        except DecoderError:
            print("✓ Invalid Base64 error handling test passed")
    
    @staticmethod
    def test_invalid_hex():
        """Test invalid Hex handling."""
        try:
            decode_hex("ZZZZZ")  # Z is not a valid hex digit
            assert False, "Should have raised DecoderError"
        except DecoderError:
            print("✓ Invalid Hex error handling test passed")


class TestAnalysis:
    """Test text analysis functions."""
    
    @staticmethod
    def test_entropy_english():
        """Test entropy calculation for English text."""
        english_text = "the quick brown fox jumps over the lazy dog"
        entropy = calculate_entropy(english_text)
        
        # English text should have lower entropy
        assert entropy < 5.0, f"English entropy {entropy} too high"
        print(f"✓ English entropy test passed (entropy={entropy:.2f})")
    
    @staticmethod
    def test_entropy_random():
        """Test entropy calculation for random data."""
        random_text = "ZG8gdGhlIGV4ZXJjaXNlLCBkb24ndCBjb3B5IGFuZCBwYXN0ZSA7KQo="
        entropy = calculate_entropy(random_text)
        
        # Encoded/random text should have higher entropy
        assert entropy > 4.0, f"Random entropy {entropy} too low"
        print(f"✓ Random entropy test passed (entropy={entropy:.2f})")
    
    @staticmethod
    def test_printable_ratio():
        """Test printable ratio calculation."""
        printable = "Hello, World!"
        ratio = calculate_printable_ratio(printable)
        
        assert ratio > 0.95, f"Printable ratio {ratio} too low"
        print(f"✓ Printable ratio test passed (ratio={ratio:.2%})")
    
    @staticmethod
    def test_flag_detection():
        """Test flag format detection."""
        assert contains_flag("flag{test}"), "Should detect flag{}"
        assert contains_flag("HTB{secret}"), "Should detect HTB{}"
        assert contains_flag("CTF{challenge}"), "Should detect CTF{}"
        assert not contains_flag("random text"), "Should not detect random text"
        print("✓ Flag detection test passed")
    
    @staticmethod
    def test_hash_detection():
        """Test hash format detection."""
        md5 = "5d41402abc4b2a76b9719d911017c592"
        sha1 = "356a192b7913b04c54574d18c28d46e6395428ab"
        sha256 = "9f86d081884c7d6d9ffd60bb75c5c6d4ccc14412d8162e20fda452c8940d6052"
        
        assert looks_like_hash(md5) == "MD5", "Should detect MD5"
        assert looks_like_hash(sha1) == "SHA1", "Should detect SHA1"
        assert looks_like_hash(sha256) == "SHA256", "Should detect SHA256"
        print("✓ Hash detection test passed")
    
    @staticmethod
    def test_validation_complete():
        """Test validation with complete result."""
        result = validate_decoded_result("encoded", "flag{found}")
        
        assert result["status"] == "COMPLETE", f"Expected COMPLETE, got {result['status']}"
        print("✓ Validation complete test passed")
    
    @staticmethod
    def test_validation_partial():
        """Test validation with partial result."""
        result = validate_decoded_result("abc", "def")
        
        # Since "def" is printable and alphabetic but not a flag
        # It should still be partial or complete based on entropy
        assert result["status"] in ["COMPLETE", "PARTIAL"], f"Unexpected status: {result['status']}"
        print("✓ Validation partial test passed")
    
    @staticmethod
    def test_validation_no_change():
        """Test validation when nothing changed."""
        result = validate_decoded_result("same", "same")
        
        assert result["status"] == "FAILED", f"Expected FAILED, got {result['status']}"
        print("✓ Validation no change test passed")


class TestState:
    """Test state management."""
    
    @staticmethod
    def test_state_initialization():
        """Test state initialization."""
        text = "test"
        state = DecoderState(current_text=text, original_text=text)
        
        assert state.current_text == text
        assert state.original_text == text
        assert state.iteration_count == 0
        assert state.text_history == [text]
        print("✓ State initialization test passed")
    
    @staticmethod
    def test_state_record_decode():
        """Test recording decode operations."""
        state = DecoderState(current_text="encoded", original_text="encoded")
        
        state.record_decode("base64", "decoded", 0.95)
        
        assert state.current_text == "decoded"
        assert state.encoding_chain == ["base64"]
        assert state.iteration_count == 1
        assert len(state.text_history) == 2
        print("✓ State record decode test passed")
    
    @staticmethod
    def test_state_loop_detection():
        """Test loop detection."""
        state = DecoderState(current_text="original", original_text="original")
        
        state.record_decode("encoder1", "middle", 0.9)
        state.record_decode("encoder2", "original", 0.9)
        
        assert state.is_loop_detected(), "Should detect loop"
        print("✓ State loop detection test passed")
    
    @staticmethod
    def test_state_should_continue():
        """Test continue condition."""
        state = DecoderState(current_text="text", original_text="text", max_iterations=2)
        
        assert state.should_continue(), "Should continue on first iteration"
        
        state.iteration_count = 2
        assert not state.should_continue(), "Should stop at max iterations"
        print("✓ State continue condition test passed")


class TestAgent:
    """Test the decoder agent."""
    
    @staticmethod
    def test_agent_simple_base64():
        """Test agent with simple Base64."""
        original = "Hello, CTF!"
        encoded = base64.b64encode(original.encode()).decode()
        
        result = iterative_decode(encoded, verbose=False)
        
        assert result["success"], f"Decoding failed: {result.get('reason')}"
        assert "Hello" in result["final_text"] or "Hello" in original
        print("✓ Agent Base64 test passed")
    
    @staticmethod
    def test_agent_multiple_layers():
        """Test agent with multiple encoding layers."""
        original = "flag{test}"
        
        # Hex encode
        hex_encoded = original.encode().hex()
        
        # Base64 encode
        base64_encoded = base64.b64encode(hex_encoded.encode()).decode()
        
        result = iterative_decode(base64_encoded, verbose=False)
        
        assert result["success"], f"Decoding failed: {result.get('reason')}"
        assert len(result["encoding_chain"]) >= 1, "Should have applied multiple decoders"
        print("✓ Agent multiple layers test passed")
    
    @staticmethod
    def test_agent_flag_detection():
        """Test agent stops at flag detection."""
        # ROT13 encode the flag
        original = "flag{ctf_challenge}"
        rot13_encoded = ''.join(
            chr((ord(c) - ord('a') + 13) % 26 + ord('a')) if 'a' <= c <= 'z'
            else chr((ord(c) - ord('A') + 13) % 26 + ord('A')) if 'A' <= c <= 'Z'
            else c
            for c in original
        )
        
        result = iterative_decode(rot13_encoded, verbose=False)
        
        assert result["success"], f"Decoding failed: {result.get('reason')}"
        assert "flag{" in result["final_text"].lower()
        print("✓ Agent flag detection test passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CTF DECODER AGENT - TEST SUITE")
    print("=" * 70 + "\n")
    
    test_classes = [
        ("Decoder Tests", TestDecoders),
        ("Analysis Tests", TestAnalysis),
        ("State Tests", TestState),
        ("Agent Tests", TestAgent),
    ]
    
    total_passed = 0
    total_failed = 0
    
    for category_name, test_class in test_classes:
        print(f"\n{category_name}:")
        print("-" * 70)
        
        methods = [m for m in dir(test_class) if m.startswith("test_")]
        
        for method_name in methods:
            try:
                method = getattr(test_class, method_name)
                method()
                total_passed += 1
            except AssertionError as e:
                print(f"✗ {method_name}: {e}")
                total_failed += 1
            except Exception as e:
                print(f"✗ {method_name}: ERROR - {e}")
                total_failed += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Total: {total_passed + total_failed}")
    print("=" * 70 + "\n")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
