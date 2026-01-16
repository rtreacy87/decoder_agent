# CTF Decoder Agent

An intelligent, iterative decoding agent for Capture The Flag (CTF) challenges. This agent automatically identifies and decodes nested encodings (Base64, Hex, ROT13, URL encoding) using the architecture described in Wiki 1.

## Features

- **Iterative Decoding**: Automatically handles nested encodings (e.g., Base64 → Hex → ROT13)
- **Smart Analysis**: Uses entropy, character set analysis, and pattern recognition to identify encodings
- **Validation**: Recognizes when decoding is complete (flag found, natural text, URLs, hashes)
- **State Management**: Tracks decoding history, encoding chain, and prevents infinite loops
- **Error Handling**: Gracefully handles decoder failures and tries alternatives
- **Configurable**: Adjustable max iterations, verbose logging, and custom parameters

## Architecture

The agent implements a five-step iterative workflow:

1. **Analyze** text characteristics (entropy, character set, length patterns)
2. **Identify** most likely encoding type based on analysis
3. **Apply** appropriate decoder tool
4. **Validate** decoded result (is it complete, partial, or failed?)
5. **Decision** point (continue loop, stop successfully, or report failure)

## Project Structure

```
decoder_agent/
├── src/
│   ├── __init__.py           # Package exports
│   ├── state.py              # DecoderState class for state management
│   ├── decoders.py           # Decoder functions (base64, hex, rot13, url)
│   ├── analysis.py           # Text analysis and validation
│   └── agent.py              # Main DecoderAgent and iterative_decode()
├── examples.py               # Usage examples
├── tests.py                  # Unit test suite
├── README.md                 # This file
├── requirements.txt          # Python dependencies
└── wiki_1_architecture.md    # Architecture documentation
```

## Installation

1. Clone the repository (or extract the project)
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
from src.agent import iterative_decode

# Decode a nested encoding
result = iterative_decode("NzM3OTZlNzQ3Yjc1MzM2Yzc5MzA1ZjZhMzA2NTc5NzE2NDdk")

if result["success"]:
    print(f"Decoded: {result['final_text']}")
    print(f"Encoding chain: {result['encoding_chain']}")
else:
    print(f"Failed: {result['reason']}")
```

### With Verbose Output

```python
from src.agent import iterative_decode

result = iterative_decode(encoded_text, verbose=True, max_iterations=10)
```

### Using the Agent Directly

```python
from src.agent import DecoderAgent

agent = DecoderAgent(max_iterations=10, verbose=True)
result = agent.decode(encoded_text)
```

### Text Analysis Only

```python
from src.analysis import print_analysis, analyze_encoding_characteristics

# Print formatted analysis
print_analysis("SGVsbG8gV29ybGQ=")

# Get analysis object
analysis = analyze_encoding_characteristics("your_text")
print(f"Entropy: {analysis.entropy}")
print(f"Printable ratio: {analysis.printable_ratio}")
print(f"Character set: {analysis.charset}")
```

## Examples

Run the example demonstrations:

```bash
python examples.py
```

This will run 6 examples:
1. Simple Base64 encoding
2. Nested Base64→Hex encoding
3. ROT13 encoding
4. Complex 3-layer nesting (Base64→ROT13→Hex)
5. URL encoding
6. Text analysis only

## Testing

Run the test suite:

```bash
python tests.py
```

This will run comprehensive tests covering:
- Decoder functions (Base64, Hex, ROT13, URL)
- Text analysis and entropy calculations
- Pattern recognition (flags, hashes, URLs)
- State management and loop detection
- Full agent integration tests

## Configuration

### Max Iterations

Control how many decode attempts before stopping:

```python
result = iterative_decode(text, max_iterations=15)
```

**Default: 10**
- Most CTF challenges use 2-4 layers
- 10 provides safety margin while preventing runaway loops

### Verbose Mode

Enable detailed logging of each iteration:

```python
result = iterative_decode(text, verbose=True)
```

Output includes:
- Current text state
- Analysis results (entropy, charset, etc.)
- Decoder selection and confidence scores
- Validation results
- Loop detection alerts

## How It Works

### Analysis Phase

The agent examines text to compute:
- **Character set**: hex, base64, alphabetic, printable, binary
- **Entropy**: Shannon entropy (4.1-4.5 for natural text, 6+ for encoded)
- **Printable ratio**: Percentage of printable characters
- **Patterns**: URL, flag format, hash format
- **Padding**: Base64 padding (= or ==)

### Encoding Identification

Based on analysis, the agent assigns confidence scores:
- **Base64**: High confidence if charset is base64 and padding detected
- **Hex**: High confidence if even length and hex-only charset
- **ROT13**: Medium confidence for alphabetic text
- **URL**: High confidence if % characters present

### Decoding & Validation

After applying a decoder, the result is validated:
- **COMPLETE**: Flag found, natural text (low entropy), URL, or hash detected
- **PARTIAL**: Still looks encoded, continue looping
- **FAILED**: No change or unreadable result

### Loop Detection

Prevents infinite loops by detecting:
1. Repeated text (already decoded this before)
2. Oscillation (A→B→A pattern)
3. Max iterations reached

## Decoder Reference

### Base64

Decodes standard Base64 encoded strings.

```python
from src.decoders import decode_base64
result = decode_base64("SGVsbG8gV29ybGQ=")  # "Hello World"
```

### Hexadecimal

Decodes hex-encoded strings.

```python
from src.decoders import decode_hex
result = decode_hex("48656c6c6f")  # "Hello"
```

### ROT13

Decodes ROT13 substitution cipher (13-letter rotation).

```python
from src.decoders import decode_rot13
result = decode_rot13("Uryyb")  # "Hello"
```

### URL (Percent-Encoding)

Decodes URL-encoded strings.

```python
from src.decoders import decode_url
result = decode_url("Hello%20World")  # "Hello World"
```

## Validation Thresholds

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| Printable Ratio | > 0.95 | Likely plain text |
| Entropy | < 4.5 | Natural language |
| Entropy | > 5.5 | Still encoded |
| Flag Pattern | Regex match | CTF flag found |

## State Management

The `DecoderState` class tracks:
- **current_text**: Current decoding state
- **encoding_chain**: List of applied decoders (["base64", "hex", ...])
- **text_history**: All intermediate results for loop detection
- **iteration_count**: Number of decode attempts
- **confidence_scores**: Agent's confidence in each decode

Access state information:

```python
from src.agent import DecoderAgent

agent = DecoderAgent()
result = agent.decode(text)

# Access detailed state
print(result['encoding_chain'])
print(result['confidence_scores'])
print(result['history'])
```

## Error Handling

The agent gracefully handles:
1. **Invalid decoder input** → Tries next decoder
2. **Multiple decoder failures** → Tries alternative approaches
3. **Unexpected errors** → Reports with traceback (verbose mode)
4. **Infinite loops** → Stops and reports loop detected

## Limitations

- Currently supports only 4 encoding types (Base64, Hex, ROT13, URL)
- No support for compression-based encodings (gzip, bzip2)
- No support for encryption (AES, RSA, etc.)
- ROT13 is trivial cipher (included for completeness)
- Limited to text-based encodings

## Future Enhancements

Potential additions for Wiki 2+:
- LLM-powered agent using smolagents framework
- Support for additional encodings (ASCII85, Base32, etc.)
- Compression decoders (gzip, bzip2)
- Advanced pattern recognition with machine learning
- Parallel decoder attempts
- Custom decoder plugins

## Testing Against Real CTF Challenges

To test with actual CTF data:

```python
from src.agent import iterative_decode

# Example from HackTheBox
ctf_encoded = "ZG8gdGhlIGV4ZXJjaXNlLCBkb24ndCBjb3B5IGFuZCBwYXN0ZSA7KQo="
result = iterative_decode(ctf_encoded, verbose=True)
```

## Contributing

To add new decoders:

1. Create decoder function in `src/decoders.py`:
   ```python
   def decode_newformat(encoded_text: str) -> str:
       """Decode newformat encoding."""
       # Implementation
       return decoded_text
   ```

2. Add to agent tools in `src/agent.py`

3. Add analysis heuristics to `src/analysis.py`

4. Add test cases to `tests.py`

## License

Educational project for CTF learning and practice.

## Support

For issues or questions:
1. Check the examples in `examples.py`
2. Run the test suite: `python tests.py`
3. Enable verbose mode: `iterative_decode(text, verbose=True)`
4. Review Wiki 1 architecture documentation

## Acknowledgments

This implementation follows the architecture design from Wiki 1 of the CTF Decoder Agent project.
