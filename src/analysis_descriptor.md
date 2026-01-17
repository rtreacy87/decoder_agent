# Analysis Module Documentation

## What is the Analysis Module?

The Analysis Module is like a detective toolkit that examines scrambled text to figure out what kind of encoding was used. It looks for clues and patterns to help the Decoder Agent decide which decoding method to try.

## Where is it?

The code is in `src/analysis.py`.

## What does it contain?

### The TextAnalysis Class

This is like a report card that stores all the information we learned about a piece of text. When you create a `TextAnalysis` object, it automatically runs all the analysis functions and stores the results.

**What it stores:**
- **text** — The text that was analyzed
- **length** — How many characters are in the text
- **charset** — What kind of characters are used (hex, base64, alphabetic, etc.)
- **padding** — Does it have special padding characters (= signs) at the end?
- **entropy** — How random/scrambled the text looks (higher = more random)
- **printable_ratio** — What percentage of characters are readable (0.0 to 1.0)
- **contains_url** — Does it have a web address in it?
- **contains_flag** — Does it look like a CTF competition flag?
- **hash_type** — Does it look like a cryptographic hash (MD5, SHA1, SHA256)?

---

## Analysis Functions (The Detectives)

### `identify_charset()`
**What it does:** Figures out what kind of characters make up the text.

**Returns:** One of these labels:
- "hex" — Only hexadecimal characters (0-9, A-F)
- "base64" — Base64 alphabet characters
- "alphabetic" — Mostly letters
- "printable" — All readable characters
- "binary" — Contains unreadable characters
- "empty" — No text at all

### `calculate_entropy()`
**What it does:** Measures how random or scrambled the text is.

**What it means:**
- Natural English text: around 4.1-4.5 bits/char
- Higher numbers = more random = probably still encoded
- Lower numbers = more predictable = possibly decoded

### `calculate_printable_ratio()`
**What it does:** Counts what fraction of characters are readable.

**Returns:** A number from 0.0 (no readable characters) to 1.0 (all readable)

### `has_padding()`
**What it does:** Checks if the text ends with "=" or "==" (a sign of Base64 encoding).

**Returns:** True or False

### `contains_url()`
**What it does:** Looks for web addresses (http:// or https://).

**Returns:** True or False

### `contains_flag()`
**What it does:** Looks for CTF flag patterns like "flag{...}" or "HTB{...}".

**Returns:** True or False

### `looks_like_hash()`
**What it does:** Checks if the text looks like a cryptographic hash by its length and character pattern.

**Returns:** 
- "MD5" (32 hex characters)
- "SHA1" (40 hex characters)
- "SHA256" (64 hex characters)
- None (not a hash)

---

## Main Analysis Functions

### `analyze_encoding_characteristics()`
**What it does:** Runs all the analysis checks at once and packages the results into a TextAnalysis object.

**Why use this?** It's a one-stop-shop to get all information about a piece of text.

### `identify_likely_encoding()`
**What it does:** Based on the analysis, gives confidence scores for different encoding types.

**Returns:** A dictionary with confidence scores (0.0 to 1.0) for:
- base64
- hex
- rot13
- url

**Example:** `{"base64": 0.95, "hex": 0.0, "rot13": 0.0, "url": 0.0}` means it's 95% confident it's Base64.

---

## Validation Functions (Quality Control)

### `validate_decoded_result()`
**What it does:** After decoding, checks if the result looks good or if we need to keep going.

**Returns:** A report with:
- **status**: "COMPLETE", "PARTIAL", or "FAILED"
- **reason**: Why we think that (e.g., "Flag format detected", "Still appears encoded")
- **confidence**: How sure we are (0.0 to 1.0)

**How it works:** Uses a series of validator functions that check things like:
1. Did anything change? (If not, FAILED)
2. Is there a flag? (If yes, COMPLETE)
3. Is there a URL? (If yes, COMPLETE)
4. Is it a hash? (If yes, COMPLETE)
5. Does it look like natural language? (If yes, COMPLETE)
6. Is it still scrambled-looking? (If yes, PARTIAL)
7. Is it somewhat readable? (If yes, PARTIAL)

### The Validator Registry

This is a system that checks decoded results in priority order. Each validator looks for specific signs:

- **_validator_no_change** — Checks if decoding changed anything
- **_validator_flag** — Looks for CTF flags (highest priority success)
- **_validator_url** — Looks for web addresses
- **_validator_hash** — Checks for hash patterns
- **_validator_natural_language** — Checks if it looks like regular text
- **_validator_still_encoded** — Checks if it still looks scrambled
- **_validator_improved_readability** — Checks if it got better but isn't perfect
- **_validator_default** — Fallback when nothing else matches

### `register_validator()`
**What it does:** A decorator that adds new validator functions to the registry.

**Why it matters:** The order validators are registered matters! Earlier validators have higher priority.

---

## Utility Functions

### `print_analysis()`
**What it does:** Prints a nice formatted report of all the analysis results.

**Use it when:** You want to see all the details about a piece of text in a readable format.

---

## How to use it

```python
from src.analysis import analyze_encoding_characteristics, identify_likely_encoding, validate_decoded_result

# Analyze some text
text = "VGhpcyBpcyBhIHRlc3Q="
analysis = analyze_encoding_characteristics(text)

print(f"Charset: {analysis.charset}")
print(f"Entropy: {analysis.entropy}")
print(f"Printable ratio: {analysis.printable_ratio}")

# Get confidence scores for different encodings
confidences = identify_likely_encoding(analysis)
print(f"Confidence scores: {confidences}")

# After decoding, validate the result
original = "VGhpcyBpcyBhIHRlc3Q="
decoded = "This is a test"
validation = validate_decoded_result(original, decoded)
print(f"Status: {validation['status']}")
print(f"Reason: {validation['reason']}")
```

## Tips

- High entropy (> 5.5) usually means the text is still encoded
- Low entropy (< 4.5) with high printable ratio (> 0.95) usually means success
- The validation system stops at the first validator that returns a result, so order matters
- Base64 text often has padding (= at the end) and length divisible by 4
