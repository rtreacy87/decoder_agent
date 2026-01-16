"""
Example usage of the CTF Decoder Agent.

This script demonstrates how to use the decoder agent with various
encoded texts.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agent import iterative_decode
from src.analysis import print_analysis


def example_1_simple_base64():
    """Example 1: Simple Base64 encoding."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Simple Base64 Encoding")
    print("=" * 70)
    
    # Create a simple Base64 encoded string
    import base64
    original = "Hello, CTF!"
    encoded = base64.b64encode(original.encode()).decode()
    
    print(f"Original: {original}")
    print(f"Encoded: {encoded}")
    
    result = iterative_decode(encoded, verbose=True)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    return result


def example_2_nested_base64_hex():
    """Example 2: Nested Base64 → Hex encoding."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Nested Base64 → Hex")
    print("=" * 70)
    
    import base64
    
    # Create nested encoding: Base64(Hex("CTF{secret}"))
    original = "CTF{secret}"
    
    # Step 1: Hex encode
    hex_encoded = original.encode().hex()
    print(f"Original: {original}")
    print(f"After Hex: {hex_encoded}")
    
    # Step 2: Base64 encode
    base64_encoded = base64.b64encode(hex_encoded.encode()).decode()
    print(f"After Base64: {base64_encoded}")
    
    result = iterative_decode(base64_encoded, verbose=True)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    return result


def example_3_rot13():
    """Example 3: ROT13 encoding."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: ROT13 Encoding")
    print("=" * 70)
    
    # Simple ROT13
    original = "flag{example_ctf_challenge}"
    rot13_encoded = ''.join(
        chr((ord(c) - ord('a') + 13) % 26 + ord('a')) if 'a' <= c <= 'z'
        else chr((ord(c) - ord('A') + 13) % 26 + ord('A')) if 'A' <= c <= 'Z'
        else c
        for c in original
    )
    
    print(f"Original: {original}")
    print(f"ROT13 Encoded: {rot13_encoded}")
    
    result = iterative_decode(rot13_encoded, verbose=True)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    return result


def example_4_complex_nesting():
    """Example 4: Complex nesting with 3+ layers."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Complex Nesting (Base64 → ROT13 → Hex)")
    print("=" * 70)
    
    import base64
    
    # Create complex nested encoding
    original = "flag{complex_encoding}"
    
    # Step 1: ROT13
    rot13_step = ''.join(
        chr((ord(c) - ord('a') + 13) % 26 + ord('a')) if 'a' <= c <= 'z'
        else chr((ord(c) - ord('A') + 13) % 26 + ord('A')) if 'A' <= c <= 'Z'
        else c
        for c in original
    )
    print(f"Original: {original}")
    print(f"After ROT13: {rot13_step}")
    
    # Step 2: Hex
    hex_step = rot13_step.encode().hex()
    print(f"After Hex: {hex_step}")
    
    # Step 3: Base64
    base64_step = base64.b64encode(hex_step.encode()).decode()
    print(f"After Base64: {base64_step}")
    
    result = iterative_decode(base64_step, verbose=True)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    return result


def example_5_url_encoding():
    """Example 5: URL encoding."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: URL Encoding")
    print("=" * 70)
    
    from urllib.parse import quote
    
    original = "flag{hello world}"
    url_encoded = quote(original)
    
    print(f"Original: {original}")
    print(f"URL Encoded: {url_encoded}")
    
    result = iterative_decode(url_encoded, verbose=True)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    return result


def example_6_analysis_only():
    """Example 6: Just analyze a text without decoding."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Text Analysis Only")
    print("=" * 70)
    
    texts = [
        "SGVsbG8sIFdvcmxkIQ==",  # Base64
        "48656c6c6f",             # Hex
        "flag{example}",           # Plain text with flag
        "guvf vf n grfg",         # ROT13
    ]
    
    for text in texts:
        print(f"\nAnalyzing: {text}")
        print("-" * 70)
        print_analysis(text)


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("CTF DECODER AGENT - EXAMPLES")
    print("=" * 70)
    
    examples = [
        ("Simple Base64", example_1_simple_base64),
        ("Nested Base64→Hex", example_2_nested_base64_hex),
        ("ROT13", example_3_rot13),
        ("Complex 3-layer", example_4_complex_nesting),
        ("URL Encoding", example_5_url_encoding),
        ("Analysis Only", example_6_analysis_only),
    ]
    
    results = {}
    
    for name, example_func in examples:
        try:
            result = example_func()
            results[name] = "SUCCESS" if result.get("success") else "FAILED"
        except Exception as e:
            print(f"\nERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = "ERROR"
    
    # Print summary
    print("\n" + "=" * 70)
    print("EXAMPLE SUMMARY")
    print("=" * 70)
    for name, status in results.items():
        print(f"  {name}: {status}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
