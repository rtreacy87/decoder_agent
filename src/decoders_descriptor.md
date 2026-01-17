# Decoders Module Documentation

## What is the Decoders Module?

The Decoders Module is a toolbox of functions that decode different types of encoded text. Each decoder knows how to unscramble one specific type of encoding. Think of it like having different keys for different locks.

## Where is it?

The code is in `src/decoders.py`.

## What encodings can it decode?

The module can decode four common encoding types:
1. **Base64** — A way to represent binary data using only letters, numbers, and a few symbols
2. **Hexadecimal (Hex)** — Data represented using 0-9 and A-F characters
3. **ROT13** — A simple letter substitution where each letter is replaced by the letter 13 positions after it
4. **URL Encoding** — Special characters in web addresses encoded with % signs

---

## The DecoderError Exception

**What it is:** A special error message that gets raised when a decoder can't decode the text.

**Why it matters:** Instead of crashing, the program can catch this error and try a different decoder.

---

## The Decoder Functions

### `decode_base64()`
**What it does:** Decodes Base64 encoded text.

**Input:** A Base64 string (looks like: "VGhpcyBpcyBhIHRlc3Q=")

**Output:** The decoded text

**Special handling:**
- If the decoded result is readable text, returns it as text
- If it contains weird characters, returns it as hex instead

**Raises:** DecoderError if the text isn't valid Base64

**Example:**
```python
result = decode_base64("VGhpcyBpcyBhIHRlc3Q=")
# Returns: "This is a test"
```

---

### `decode_hex()`
**What it does:** Decodes hexadecimal encoded text.

**Input:** A hex string (looks like: "48656c6c6f")

**Output:** The decoded text

**Special behavior:**
- Removes spaces, tabs, and newlines automatically
- Checks that all characters are valid hex (0-9, A-F)
- Makes sure the length is even (hex comes in pairs)
- If the decoded result can't be read as text, returns it as Base64 instead

**Raises:** DecoderError if:
- Text has odd length
- Text contains non-hex characters

**Example:**
```python
result = decode_hex("48656c6c6f")
# Returns: "Hello"
```

---

### `decode_rot13()`
**What it does:** Decodes ROT13 encoded text.

**What is ROT13?** A simple code where:
- A becomes N
- B becomes O
- ...
- M becomes Z
- N becomes A
- etc.

**Special notes:**
- Only letters are changed
- Numbers, spaces, and punctuation stay the same
- Works the same forwards and backwards (decoding is the same as encoding!)

**Raises:** DecoderError if something goes wrong

**Example:**
```python
result = decode_rot13("Uryyb Jbeyq")
# Returns: "Hello World"
```

---

### `decode_url()`
**What it does:** Decodes URL (percent) encoded text.

**What is URL encoding?** Special characters are replaced with % followed by two hex digits.
- Space becomes %20
- @ becomes %40
- ! becomes %21

**Input:** Text with % encodings (looks like: "Hello%20World%21")

**Output:** The decoded text with special characters restored

**Checks:**
- Makes sure the text contains at least one % sign
- Makes sure something actually changed after decoding

**Raises:** DecoderError if:
- No % signs found
- Decoding didn't change anything

**Example:**
```python
result = decode_url("Hello%20World%21")
# Returns: "Hello World!"
```

---

## Helper Functions

### `try_all_decoders()`
**What it does:** Tries every decoder to see which ones work.

**Input:** Any encoded text

**Output:** A list of successful results as tuples: `(decoder_name, decoded_text)`

**Why use this?** When you don't know which encoding was used, this tries them all and tells you which ones worked.

**Important:** Only returns decoders that actually changed the text (filters out ones that returned the same thing).

**Example:**
```python
results = try_all_decoders("VGhpcyBpcyBhIHRlc3Q=")
# Returns: [("base64", "This is a test")]
```

---

## How to use it

### Using individual decoders:

```python
from src.decoders import decode_base64, decode_hex, decode_rot13, decode_url, DecoderError

# Decode Base64
try:
    result = decode_base64("VGhpcyBpcyBhIHRlc3Q=")
    print(result)
except DecoderError as e:
    print(f"Failed: {e}")

# Decode hex
result = decode_hex("48656c6c6f")
print(result)  # "Hello"

# Decode ROT13
result = decode_rot13("Uryyb")
print(result)  # "Hello"

# Decode URL
result = decode_url("Hello%20World")
print(result)  # "Hello World"
```

### Testing all decoders at once:

```python
from src.decoders import try_all_decoders

text = "VGhpcyBpcyBhIHRlc3Q="
results = try_all_decoders(text)

for decoder_name, decoded_text in results:
    print(f"{decoder_name}: {decoded_text}")
```

---

## Tips for using decoders

- **Always use try/except** when calling individual decoders, since they can raise DecoderError
- **Use try_all_decoders()** when you're not sure which encoding was used
- **Base64 text** usually ends with = or == and has length divisible by 4
- **Hex text** has even length and only uses characters 0-9 and A-F
- **ROT13** only affects letters, so if you see numbers or symbols, those stay the same
- **URL encoding** always has % signs in it

## Common scenarios

**Scenario 1: You know it's Base64**
```python
result = decode_base64(my_text)
```

**Scenario 2: You're not sure what it is**
```python
results = try_all_decoders(my_text)
if results:
    print(f"It might be {results[0][0]}: {results[0][1]}")
```

**Scenario 3: You want to try each decoder manually**
```python
from src.decoders import decode_base64, decode_hex, DecoderError

try:
    result = decode_base64(my_text)
    print("Success with Base64!")
except DecoderError:
    try:
        result = decode_hex(my_text)
        print("Success with Hex!")
    except DecoderError:
        print("Neither worked")
```
