# Wiki 1: Architecture of an Iterative CTF Decoding Agent

## Overview

In this wiki, we'll design the architecture for an iterative CTF decoding agent using the smolagents framework. This agent will automatically identify and decode nested encodings commonly found in Capture The Flag (CTF) challenges—such as Base64 wrapped in Hex wrapped in ROT13.

By the end of this wiki, you'll understand:
- Why iterative decoding is necessary for CTF challenges
- How to design an agent workflow that intelligently handles encoding chains
- What state management and validation strategies are needed
- Why smolagents is particularly well-suited for this task

---

## 1. The Iterative Decoding Challenge

### 1.1 What Are Nested Encodings?

In CTF challenges, obfuscated data is rarely encoded just once. Challenge creators often chain multiple encoding methods together to increase difficulty. For example:

```
Original:  flag{h3ll0_w0rld}
Step 1:    ROT13 encode    → synt{u3yy0_j0eyq}
Step 2:    Hex encode      → 73796e747b75336c79305f6a30657971647d
Step 3:    Base64 encode   → NzM3OTZlNzQ3Yjc1MzM2Yzc5MzA1ZjZhMzA2NTc5NzE2NDdk
```

To recover the flag, you must decode in reverse order: Base64 → Hex → ROT13.

### 1.2 Real CTF Example

From the HackTheBox documentation provided, we see this encoded string:

```
ZG8gdGhlIGV4ZXJjaXNlLCBkb24ndCBjb3B5IGFuZCBwYXN0ZSA7KQo=
```

This is Base64 encoded text. But in a real challenge, this might be:

```
NjM3NTY3NGM3NDY4NjUyMDY1Nzg2NTcyNjM2OTczNjUyYzIwNjQ2ZjZlMjc3NDIwNjM2ZjcwNzkyMDYxNmU2NDIwNzA2MTczNzQ2NTIwM2IyOTBh
```

Which requires: Base64 → Hex → Base64 again to fully decode.

### 1.3 Why Simple Sequential Testing Fails

A naive approach might try each decoder sequentially:

```python
# ❌ Bad approach
result = try_base64(input)
if not success:
    result = try_hex(input)
if not success:
    result = try_rot13(input)
# ...
```

**Problems with this approach:**

1. **No iteration**: Stops after one decode, missing nested encodings
2. **No intelligence**: Doesn't analyze the input to pick the best decoder first
3. **No validation**: Can't determine if decoding was successful or if more layers remain
4. **No loop detection**: Could get stuck in infinite loops
5. **No state tracking**: Can't report which encodings were used

### 1.4 Why We Need an Intelligent Agent

An agent-based approach solves these problems:

- **Iterative reasoning**: The LLM can analyze, decode, then re-analyze the result
- **Pattern recognition**: Recognizes encoding characteristics (padding, character sets)
- **Decision making**: Chooses the most likely decoder based on analysis
- **Validation**: Determines when decoding is complete
- **State tracking**: Maintains history of applied decodings

---

## 2. Agent Workflow Design

### 2.1 The Five-Step Iterative Loop

Our agent follows this cycle until the text is fully decoded:

```
┌─────────────────────────────────────────────┐
│                                             │
│  STEP 1: Analyze String Characteristics    │
│  ├─ Character set (hex? base64? printable?)│
│  ├─ Length patterns                         │
│  ├─ Padding indicators                      │
│  └─ Entropy/randomness                      │
│                                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│                                             │
│  STEP 2: Identify Most Likely Encoding     │
│  ├─ Base64 (ends with =, ==)?              │
│  ├─ Hex (even length, 0-9a-f only)?       │
│  ├─ ROT13 (alphabetic with patterns)?     │
│  └─ URL encoding (%XX patterns)?           │
│                                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│                                             │
│  STEP 3: Apply Appropriate Decoder Tool    │
│  ├─ Call decode_base64()                   │
│  ├─ Call decode_hex()                      │
│  ├─ Call decode_rot13()                    │
│  └─ Or call decode_url()                   │
│                                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│                                             │
│  STEP 4: Validate Decoded Result           │
│  ├─ Is it more readable than before?       │
│  ├─ Does it contain a flag format?         │
│  ├─ Is it printable text or still encoded? │
│  └─ Check entropy (randomness) decrease    │
│                                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│                                             │
│  STEP 5: Decision Point                    │
│  ├─ Still encoded? → Loop back to Step 1   │
│  ├─ Fully decoded? → Report final result   │
│  ├─ Max iterations? → Report partial result│
│  └─ Loop detected? → Report and stop       │
│                                             │
└─────────────────────────────────────────────┘
```

### 2.2 Detailed Step Breakdown

#### Step 1: Analyze String Characteristics

The agent examines the input to gather clues:

```python
# Pseudocode for analysis
characteristics = {
    "length": len(text),
    "charset": identify_charset(text),  # "base64", "hex", "alphanumeric", "printable"
    "padding": has_padding(text),       # True if ends with = or ==
    "entropy": calculate_entropy(text), # High = random/encoded, Low = natural text
    "patterns": {
        "url_scheme": contains_url(text),      # http://, https://
        "flag_format": contains_flag(text),    # flag{...}, HTB{...}
        "hash_format": looks_like_hash(text),  # 32 or 40 char hex
    }
}
```

**Key characteristics to identify:**

| Encoding | Length Pattern | Character Set | Padding | Entropy |
|----------|---------------|---------------|---------|---------|
| Base64 | Multiple of 4 | A-Za-z0-9+/ | = or == | High |
| Hex | Even number | 0-9a-f | None | High |
| ROT13 | Any | A-Za-z | None | Medium |
| URL | Any | A-Za-z0-9%- | None | Medium-High |
| Plain text | Any | Printable ASCII | None | Low |

#### Step 2: Identify Most Likely Encoding

Based on the analysis, the agent ranks possible encodings:

```python
# Pseudocode for identification
if characteristics["padding"] and characteristics["charset"] == "base64":
    most_likely = "base64"
    confidence = 0.95
elif characteristics["length"] % 2 == 0 and characteristics["charset"] == "hex":
    most_likely = "hex"
    confidence = 0.90
elif "%" in text:
    most_likely = "url"
    confidence = 0.85
elif characteristics["charset"] == "alphabetic":
    most_likely = "rot13"
    confidence = 0.70
else:
    most_likely = "unknown"
    confidence = 0.30
```

**Decision strategy**: Try the highest confidence decoder first, but be prepared to try alternatives if it fails.

#### Step 3: Apply Appropriate Decoder Tool

The agent calls the selected decoder tool:

```python
# Using smolagents @tool decorated functions
result = decode_base64(encoded_text)
# or
result = decode_hex(encoded_text)
# or
result = decode_rot13(encoded_text)
```

**Error handling**: If decoding fails (invalid format), the agent should try the next most likely encoding.

#### Step 4: Validate Decoded Result

After decoding, the agent must determine if the result is:
- **Fully decoded**: Natural text, contains a flag, or is clearly the final answer
- **Partially decoded**: Still encoded but made progress (different encoding detected)
- **Failed decode**: Same as input or produced garbage

```python
# Pseudocode for validation
def validate_result(original, decoded):
    # Same as input = failed
    if original == decoded:
        return "FAILED"
    
    # Check if it's human-readable
    printable_ratio = count_printable(decoded) / len(decoded)
    if printable_ratio > 0.95:
        # Check for flag formats
        if contains_flag_pattern(decoded):
            return "COMPLETE"  # Found the flag!
        # Check if it's natural English/readable text
        if entropy(decoded) < threshold:
            return "COMPLETE"  # Looks like plain text
        return "PARTIAL"  # Readable but might need more decoding
    
    # Still looks encoded
    if still_looks_encoded(decoded):
        return "PARTIAL"  # Made progress, continue decoding
    
    return "FAILED"
```

#### Step 5: Decision Point

Based on validation results:

```python
# Pseudocode for decision logic
validation_result = validate_result(current_text, decoded_text)

if validation_result == "COMPLETE":
    report_success(decoded_text, encoding_chain)
    
elif validation_result == "PARTIAL":
    if iteration_count < MAX_ITERATIONS:
        encoding_chain.append(encoding_used)
        current_text = decoded_text
        continue_loop()  # Back to Step 1
    else:
        report_partial(decoded_text, encoding_chain)
        
elif validation_result == "FAILED":
    try_alternative_decoder()
    if no_more_alternatives:
        report_failure(current_text, encoding_chain)
```

### 2.3 Why This Design Works with smolagents

The **smolagents framework** is ideal for this iterative workflow because:

1. **Code Agents**: Generate Python code directly, allowing complex logic like loops and state tracking
2. **Tool Integration**: Easily wraps decoder functions as tools the agent can call
3. **Multi-Step Execution**: Built-in support for iterative reasoning via `MultiStepAgent`
4. **State Logging**: Automatically tracks `ActionStep` history for debugging
5. **Local Models**: Works with Ollama for offline CTF environments

From the smolagents documentation:

> *"Code agents generate Python tool calls to perform actions, achieving action representations that are efficient, expressive, and accurate. Their streamlined approach reduces the number of required actions, simplifies complex operations, and enables reuse of existing code functions."*

---

## 3. State Management

### 3.1 Why State Management Matters

In an iterative decoding loop, we must track:
- **Current text state**: The most recent decoded result
- **Encoding chain**: Which decoders were applied in order
- **Iteration count**: How many loops we've completed
- **History**: Previous results to detect loops

Without proper state management, the agent could:
- Lose track of progress
- Repeat unsuccessful decodings
- Get stuck in infinite loops
- Be unable to report the decoding path

### 3.2 State Variables to Track

```python
class DecoderState:
    """State management for iterative decoding"""
    
    def __init__(self, initial_text: str, max_iterations: int = 10):
        # Core state
        self.current_text: str = initial_text
        self.original_text: str = initial_text
        
        # History tracking
        self.encoding_chain: List[str] = []  # e.g., ["base64", "hex", "rot13"]
        self.text_history: List[str] = [initial_text]  # All intermediate results
        
        # Loop control
        self.iteration_count: int = 0
        self.max_iterations: int = max_iterations
        
        # Status
        self.is_complete: bool = False
        self.completion_reason: str = ""  # "flag_found", "max_iterations", "loop_detected", etc.
        
        # Metadata
        self.confidence_scores: List[float] = []  # Confidence of each decode
        self.attempted_decodings: Set[Tuple[str, str]] = set()  # (text, decoder) pairs tried
```

### 3.3 Recording Encoding Chain

Each successful decode adds to the chain:

```python
def record_decode(self, encoding_type: str, result: str, confidence: float):
    """Record a successful decode operation"""
    self.encoding_chain.append(encoding_type)
    self.text_history.append(result)
    self.current_text = result
    self.confidence_scores.append(confidence)
    self.iteration_count += 1
    
    # Mark this attempt as tried
    self.attempted_decodings.add((self.text_history[-2], encoding_type))
```

**Example encoding chain**:
```python
state.encoding_chain = ["base64", "hex", "rot13"]
# Means: input was base64 → decoded to hex → decoded to rot13 → final result
```

### 3.4 Loop Detection

To prevent infinite loops, we check if:
1. We've seen this exact text before
2. We've tried this decoder on this text before
3. We're alternating between two states

```python
def is_loop_detected(self) -> bool:
    """Detect if we're in a decoding loop"""
    # Check if current text appeared before
    if self.current_text in self.text_history[:-1]:
        return True
    
    # Check if we're trying the same decoder on the same text
    last_text = self.text_history[-2] if len(self.text_history) > 1 else None
    if last_text and self.current_text == last_text:
        return True
    
    # Check for oscillation (A→B→A→B pattern)
    if len(self.text_history) >= 4:
        if (self.text_history[-1] == self.text_history[-3] and 
            self.text_history[-2] == self.text_history[-4]):
            return True
    
    return False
```

### 3.5 Iteration Counting

```python
def should_continue(self) -> bool:
    """Determine if decoding should continue"""
    if self.is_complete:
        return False
    if self.iteration_count >= self.max_iterations:
        self.completion_reason = "max_iterations_reached"
        return False
    if self.is_loop_detected():
        self.completion_reason = "loop_detected"
        return False
    return True
```

### 3.6 State Persistence (Optional)

For debugging or review, state can be serialized:

```python
def to_dict(self) -> dict:
    """Export state as dictionary"""
    return {
        "original_text": self.original_text,
        "final_text": self.current_text,
        "encoding_chain": self.encoding_chain,
        "iterations": self.iteration_count,
        "complete": self.is_complete,
        "reason": self.completion_reason,
        "history": self.text_history,
        "confidence_scores": self.confidence_scores
    }
```

---

## 4. Validation Strategies

### 4.1 Character Set Analysis

**Printable Ratio**: Percentage of printable ASCII characters

```python
import string

def calculate_printable_ratio(text: str) -> float:
    """Calculate ratio of printable characters"""
    if not text:
        return 0.0
    
    printable_count = sum(1 for c in text if c in string.printable)
    return printable_count / len(text)

# Usage
ratio = calculate_printable_ratio(decoded_text)
if ratio > 0.95:
    print("Likely decoded successfully")
elif ratio > 0.80:
    print("Partially decoded or contains binary")
else:
    print("Still encoded or corrupted")
```

**Validation thresholds**:
- ratio > 0.95: Likely plain text
- 0.80 < ratio ≤ 0.95: Mixed content
- ratio ≤ 0.80: Still encoded

### 4.2 Entropy Calculations

**Entropy** measures randomness/unpredictability in text. Encoded text has higher entropy than natural language.

```python
import math
from collections import Counter

def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of text"""
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

# Usage
entropy = calculate_entropy(text)
```

**Entropy benchmarks**:
- English text: ~4.1-4.5 bits/char
- Base64: ~6.0 bits/char
- Hex: ~4.0 bits/char (but uniform distribution)
- Random binary: ~8.0 bits/char

**Validation logic**:
```python
if entropy < 4.5:
    print("Likely natural language")
elif 4.5 <= entropy < 6.0:
    print("Might be encoded or technical text")
else:
    print("Highly random - still encoded")
```

### 4.3 Pattern Recognition

**URL Detection**:
```python
import re

def contains_url(text: str) -> bool:
    """Check if text contains URL patterns"""
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, text))
```

**Flag Format Detection** (CTF-specific):
```python
def contains_flag(text: str) -> bool:
    """Check for common CTF flag formats"""
    flag_patterns = [
        r'flag\{[^\}]+\}',     # flag{...}
        r'HTB\{[^\}]+\}',      # HTB{...}
        r'CTF\{[^\}]+\}',      # CTF{...}
        r'picoCTF\{[^\}]+\}',  # picoCTF{...}
    ]
    
    for pattern in flag_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
```

**Hash Format Detection**:
```python
def looks_like_hash(text: str) -> Optional[str]:
    """Identify if text looks like a hash"""
    text = text.strip()
    
    # MD5: 32 hex chars
    if len(text) == 32 and all(c in '0123456789abcdefABCDEF' for c in text):
        return "MD5"
    
    # SHA1: 40 hex chars
    if len(text) == 40 and all(c in '0123456789abcdefABCDEF' for c in text):
        return "SHA1"
    
    # SHA256: 64 hex chars
    if len(text) == 64 and all(c in '0123456789abcdefABCDEF' for c in text):
        return "SHA256"
    
    return None
```

### 4.4 Combined Validation Function

```python
def validate_decoded_result(original: str, decoded: str) -> dict:
    """Comprehensive validation of decode result"""
    
    # No change = failed
    if original == decoded:
        return {
            "status": "FAILED",
            "reason": "No change after decoding",
            "confidence": 0.0
        }
    
    # Calculate metrics
    printable_ratio = calculate_printable_ratio(decoded)
    entropy = calculate_entropy(decoded)
    
    # Check patterns
    has_flag = contains_flag(decoded)
    has_url = contains_url(decoded)
    hash_type = looks_like_hash(decoded)
    
    # Decision logic
    if has_flag:
        return {
            "status": "COMPLETE",
            "reason": "Flag format detected",
            "confidence": 0.99
        }
    
    if printable_ratio > 0.95 and entropy < 4.5:
        return {
            "status": "COMPLETE",
            "reason": "Natural language detected",
            "confidence": 0.90
        }
    
    if has_url:
        return {
            "status": "COMPLETE",
            "reason": "URL detected",
            "confidence": 0.85
        }
    
    if hash_type:
        return {
            "status": "COMPLETE",
            "reason": f"{hash_type} hash detected",
            "confidence": 0.80
        }
    
    # Still looks encoded
    if printable_ratio < 0.80 or entropy > 5.5:
        return {
            "status": "PARTIAL",
            "reason": "Still appears encoded",
            "confidence": 0.60
        }
    
    # Ambiguous
    return {
        "status": "PARTIAL",
        "reason": "Ambiguous result",
        "confidence": 0.50
    }
```

---

## 5. Architecture Decisions

### 5.1 Max Iterations Limit

**Default: 10 iterations**

**Rationale**:
- Most CTF challenges use 2-4 encoding layers
- 10 iterations provides safety margin
- Prevents infinite loops from consuming resources

**Configurable per use case**:
```python
# For simple challenges
agent = IterativeDecoderAgent(max_iterations=5)

# For complex/unknown challenges
agent = IterativeDecoderAgent(max_iterations=15)

# For automated scanning
agent = IterativeDecoderAgent(max_iterations=3)  # Faster
```

### 5.2 When to Stop Decoding

**Stop conditions (in priority order)**:

1. **Flag detected**: Highest priority - we found what we're looking for
2. **Natural text detected**: Printable ratio > 95% and low entropy
3. **Max iterations reached**: Safety limit hit
4. **Loop detected**: Same result appearing twice
5. **No progress**: Multiple decoders failed on current text
6. **Error threshold**: Too many decoder errors

**Implementation**:
```python
def should_stop(state: DecoderState, validation: dict) -> Tuple[bool, str]:
    """Determine if decoding should stop"""
    
    # Success conditions
    if validation["status"] == "COMPLETE":
        return True, validation["reason"]
    
    # Safety conditions
    if state.iteration_count >= state.max_iterations:
        return True, "Maximum iterations reached"
    
    if state.is_loop_detected():
        return True, "Loop detected"
    
    # No progress conditions
    if state.iteration_count > 3:
        recent_confidence = state.confidence_scores[-3:]
        if all(c < 0.3 for c in recent_confidence):
            return True, "No significant progress"
    
    return False, ""
```

### 5.3 Error Handling Approach

**Strategy: Graceful degradation with informative feedback**

**Three types of errors**:

1. **Decoder errors**: Invalid format for a specific encoding
   - Action: Try next most likely decoder
   - Logging: Record which decoders failed
   
2. **Agent errors**: LLM fails to generate valid code
   - Action: Retry with simplified prompt
   - Logging: Capture agent output for debugging
   
3. **System errors**: Connection issues, resource limits
   - Action: Stop gracefully, report partial results
   - Logging: Full error traceback

**Error handling pseudocode**:
```python
class DecoderAgent:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    def decode_iteration(self, state: DecoderState) -> DecoderResult:
        """Single decode iteration with error handling"""
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                # Analyze text
                analysis = self.analyze_text(state.current_text)
                
                # Select decoder
                decoder = self.select_decoder(analysis)
                
                # Apply decoder
                result = decoder(state.current_text)
                
                # Validate
                validation = validate_decoded_result(
                    state.current_text, 
                    result
                )
                
                return DecoderResult(
                    success=True,
                    decoded_text=result,
                    encoding_used=decoder.name,
                    validation=validation
                )
                
            except DecoderError as e:
                # Try alternative decoder
                last_error = e
                retry_count += 1
                continue
                
            except AgentError as e:
                # Agent failed to generate valid code
                last_error = e
                if retry_count < self.max_retries - 1:
                    self.simplify_prompt()
                retry_count += 1
                continue
                
            except Exception as e:
                # Unexpected error - stop gracefully
                return DecoderResult(
                    success=False,
                    error=str(e),
                    partial_result=state.current_text
                )
        
        # All retries exhausted
        return DecoderResult(
            success=False,
            error=f"All retries exhausted: {last_error}",
            partial_result=state.current_text
        )
```

**Error reporting format**:
```python
{
    "success": False,
    "final_text": "NzM3OTZlNzQ...",  # Last successful decode
    "encoding_chain": ["base64", "hex"],  # Successful decodes
    "failed_at": "rot13",  # Where it failed
    "error": "Invalid ROT13 input: contains digits",
    "iterations": 3,
    "partial_decoding": True
}
```

### 5.4 Agent vs. Loop Control Architecture

**Two possible architectures**:

**Option A: Agent-Controlled Loop** (Higher-level)
```python
# Agent manages everything internally
agent.run("""
Decode this text iteratively:
{encoded_text}

Keep decoding until you find plain text or a flag.
Track each encoding you apply.
""")
```

**Pros**:
- Simpler code
- Agent has full autonomy
- More flexible reasoning

**Cons**:
- Less predictable
- Harder to debug
- May not follow exact workflow

---

**Option B: Python-Controlled Loop** (Lower-level)
```python
# Python manages the loop explicitly
state = DecoderState(encoded_text)

while state.should_continue():
    # Agent does one decode step
    result = agent.run(f"""
    Analyze and decode this text one step:
    {state.current_text}
    
    Return: (encoding_type, decoded_text, confidence)
    """)
    
    # Python manages state
    state.record_decode(result.encoding, result.text, result.confidence)
    
    # Python validates
    validation = validate_decoded_result(state.current_text, result.text)
    if validation["status"] == "COMPLETE":
        break
```

**Pros**:
- Full control over loop logic
- Guaranteed loop detection
- Easier to debug and test
- Predictable behavior

**Cons**:
- More code to write
- Agent has less autonomy

**Recommendation**: Start with Option B (Python-controlled) for predictability, then experiment with Option A if needed.

---

## 6. Complete Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                   CTF DECODER AGENT                      │
│                                                          │
└────────────────────┬─────────────────────────────────────┘
                     │
                     │ Encoded Input
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│                    STATE MANAGER                         │
│  ├─ current_text                                         │
│  ├─ encoding_chain: []                                   │
│  ├─ iteration_count: 0                                   │
│  └─ text_history: []                                     │
└────────────────────┬─────────────────────────────────────┘
                     │
                     │ Current State
                     │
        ┌────────────┼────────────────┐
        │            │                │
        ▼            ▼                ▼
┌───────────┐   ┌──────────┐   ┌────────────┐
│ STEP 1  │   │ STEP 2  │   │  STEP 3    │
│ Analyze │ ──> │ Identify │ ──> │  Decode    │
│  Text   │   │ Encoding │   │  (Tools)   │
└───────────┘   └──────────┘   └────────────┘
     │              │                │
     │              │                │
     │         ┌────┴────────────────┐    │
     │         │                     │    │
     │         │   DECODER TOOLS     │    │
     │         │   ├─ decode_base64  │    │
     │         │   ├─ decode_hex     │    │
     │         │   ├─ decode_rot13   │<───┘
     │         │   └─ decode_url     │
     │         │                     │
     │         └─────────────────────┘
     │                                    
     │                 Decoded Result
     │                      │
     │                      ▼
     │         ┌────────────────────┐
     │         │    STEP 4          │
     └─────────> │   Validate         │
               │   Result           │
               └──────────┬─────────┘
                          │
                          │ Validation Result
                          │
                          ▼
               ┌────────────────────┐
               │   STEP 5          │
               │   Decision        │
               └────────┬───────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌───────┐   ┌─────────┐   ┌────────┐
    │ LOOP  │   │ STOP    │   │ REPORT │
    │ BACK  │   │ (Max    │   │ FINAL  │
    │       │   │  Iter)  │   │ RESULT │
    └───┬───┘   └─────────┘   └────────┘
        │
        │ Update State
        │ encoding_chain.append(...)
        │
        └────────────────────────┐
                                 │
                        (Loop to Step 1)
```

---

## 7. Workflow Flowchart

```
                        START
                          │
                          ▼
              ┌──────────────────┐
              │ Initialize State │
              │ - current_text   │
              │ - iteration = 0  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Analyze Text     │───┐
              │ - charset        │   │
              │ - length         │   │
              │ - entropy        │   │
              └────────┬─────────┘   │
                       │            │
                       ▼            │
              ┌──────────────────┐  │
              │ Identify         │  │
              │ Encoding Type    │  │  Analysis
              └────────┬─────────┘  │  Tools
                       │            │
                       ▼            │
              ┌──────────────────┐  │
              │ Apply Decoder    │<─┘
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Decoder Success? │
              └───┬────────┬─────┘
                  │ Yes    │ No
                  ▼        ▼
          ┌─────────┐    ┌─────────────┐
          │ Update  │    │ Try Next    │
          │ State   │    │ Decoder?    │
          └───┬─────┘    └───┬─────┬───┘
              │              │ Yes │ No
              │              │     │
              │              └─────┼────> FAIL
              ▼                    │
    ┌─────────────────┐            │
    │ Validate Result │            │
    └───┬─────────────┘            │
        │                          │
        ▼                          │
    ┌───────────────┐              │
    │ Still Encoded?│              │
    └─┬─────────┬───┘              │
      │ Yes     │ No               │
      ▼         ▼                  │
   ┌──────┐  ┌───────────┐        │
   │Loop? │  │ Flag Found?│        │
   └─┬─┬──┘  └─┬───────┬─┘        │
     │ │       │ Yes   │ No       │
  Yes│ │No     ▼       ▼          │
     │ │    SUCCESS   ┌───────────┐
     │ │              │ Max Iter? │
     │ │              └─┬─────┬───┘
     │ │                │Yes  │No
     │ │                ▼     ▼
     │ │              STOP  CONTINUE
     │ │                │     │
     │ │                │     └────────────┘
     │ └────────────────┘
     │
     │ Loop detected
     ▼
   ERROR
```

---

## 8. Pseudocode for Main Loop

### Python-Controlled Loop (Recommended)

```python
def iterative_decode(encoded_text: str, max_iterations: int = 10) -> dict:
    """
    Main iterative decoding function
    
    Args:
        encoded_text: The text to decode
        max_iterations: Maximum decode attempts
        
    Returns:
        Dictionary with decoding results
    """
    # Initialize state
    state = DecoderState(
        initial_text=encoded_text,
        max_iterations=max_iterations
    )
    
    # Initialize agent
    agent = CodeAgent(
        tools=[
            analyze_encoding_characteristics,
            decode_base64,
            decode_hex,
            decode_rot13,
            decode_url,
            validate_decoded_result,
            validate_ctf_flag
        ],
        model=LocalOllamaModel("qwen2.5-coder:7b"),
        max_steps=3,  # Low: we control the loop
        verbosity_level=1
    )
    
    # Main decoding loop
    while state.should_continue():
        try:
            # Agent performs one decode iteration
            result = agent.run(f"""
            Analyze this text and decode it ONE step:
            
            Text: {state.current_text}
            
            Instructions:
            1. Use analyze_encoding_characteristics() to examine the text
            2. Based on the analysis, select the most likely encoding
            3. Apply the appropriate decoder tool
            4. Return the decoded result
            
            Return format:
            - encoding_type: the encoding you detected
            - decoded_text: the result after decoding
            - confidence: your confidence (0.0-1.0)
            """)
            
            # Parse agent result
            encoding_type = result['encoding_type']
            decoded_text = result['decoded_text']
            confidence = result['confidence']
            
            # Check if we made progress
            if decoded_text == state.current_text:
                state.completion_reason = "no_progress"
                break
            
            # Validate the result
            validation = validate_decoded_result(
                state.current_text, 
                decoded_text
            )
            
            # Record the decode
            state.record_decode(
                encoding_type, 
                decoded_text, 
                confidence
            )
            
            # Check completion conditions
            if validation["status"] == "COMPLETE":
                state.is_complete = True
                state.completion_reason = validation["reason"]
                break
            
            # Check for loops
            if state.is_loop_detected():
                state.completion_reason = "loop_detected"
                break
            
            # Continue with decoded result
            state.current_text = decoded_text
            
        except Exception as e:
            # Handle errors gracefully
            state.completion_reason = f"error: {str(e)}"
            break
    
    # Return final results
    return {
        "success": state.is_complete,
        "original_text": state.original_text,
        "final_text": state.current_text,
        "encoding_chain": state.encoding_chain,
        "iterations": state.iteration_count,
        "reason": state.completion_reason,
        "confidence_scores": state.confidence_scores,
        "full_history": state.text_history
    }
```

---

## 9. Validation Criteria Reference

### Summary Table

| Criterion | Threshold | Indicates |
|-----------|-----------|-----------|
| **Printable Ratio** | > 0.95 | Likely plain text |
| | 0.80-0.95 | Mixed/partial decode |
| | < 0.80 | Still encoded |
| **Entropy** | < 4.5 | Natural language |
| | 4.5-6.0 | Technical/encoded |
| | > 6.0 | Random/encrypted |
| **Flag Pattern** | Regex match | CTF flag found |
| **URL Pattern** | Regex match | Valid URL |
| **Hash Pattern** | 32/40/64 hex | MD5/SHA1/SHA256 |
| **Base64 Padding** | Ends with =, == | Likely Base64 |
| **Hex Pattern** | Even length, 0-9a-f | Likely Hex |
| **Progress** | Text changed | Decode successful |
| **No Progress** | Text unchanged | Decode failed |

### Validation Decision Tree

```
Is text different from input?
├─ NO → FAILED (no change)
└─ YES → Continue...
    │
    Does it contain flag{...} or HTB{...}?
    ├─ YES → COMPLETE (flag found) ✅
    └─ NO → Continue...
        │
        Is printable_ratio > 0.95 AND entropy < 4.5?
        ├─ YES → COMPLETE (natural text) ✅
        └─ NO → Continue...
            │
            Does it contain http:// or https://?
            ├─ YES → COMPLETE (URL found) ✅
            └─ NO → Continue...
                │
                Is it a hash (32/40/64 hex chars)?
                ├─ YES → COMPLETE (hash found) ✅
                └─ NO → Continue...
                    │
                    Is printable_ratio < 0.80 OR entropy > 5.5?
                    ├─ YES → PARTIAL (still encoded) 🔄
                    └─ NO → PARTIAL (ambiguous) ❓
```

---

## Deliverables

To ensure this wiki is complete and you're ready to move to implementation, verify you can produce the following:

### ✅ Deliverable 1: High-Level Architecture Diagram

**Task**: Create a visual diagram showing:
- The five main steps (Analyze → Identify → Decode → Validate → Decision)
- State manager component
- Tool collection (decoders)
- Loop flow with decision points

**Acceptance Criteria**:
- All five steps clearly labeled
- Arrows showing data flow
- State manager position clear
- Loop-back path visible

**Format**: ASCII art (as shown above) or a diagram tool (draw.io, Excalidraw, etc.)

---

### ✅ Deliverable 2: Detailed Workflow Flowchart

**Task**: Create a flowchart showing:
- All decision points (Yes/No branches)
- Success/failure/partial outcomes
- Loop detection logic
- Max iterations check

**Acceptance Criteria**:
- Every decision node has two branches
- Terminal states (SUCCESS, STOP, FAIL) clearly marked
- Loop-back path visible
- Can trace any scenario through the flowchart

**Format**: ASCII art (as shown above) or flowchart tool

---

### ✅ Deliverable 3: Pseudocode for Main Loop

**Task**: Write detailed pseudocode showing:
- State initialization
- Agent setup
- Loop structure
- Error handling
- Result formatting

**Acceptance Criteria**:
- Complete function signature
- All state variables initialized
- Agent run call with proper prompt
- Validation logic included
- Error handling present
- Return value structure defined

**Example Format**:
```python
def iterative_decode(encoded_text: str, max_iterations: int = 10) -> dict:
    # Your pseudocode here
    pass
```

---

### ✅ Deliverable 4: Validation Criteria Document

**Task**: Create a reference document listing:
- All validation metrics (printable ratio, entropy, patterns)
- Thresholds for each metric
- Decision logic combining multiple metrics
- Example calculations

**Acceptance Criteria**:
- Table with metrics and thresholds (as shown above)
- Decision tree for validation (as shown above)
- At least 3 example calculations
- Clear "COMPLETE" vs "PARTIAL" vs "FAILED" definitions

**Format**: Markdown table + decision tree

---

### ✅ Deliverable 5: State Management Design

**Task**: Document the state structure:
- All state variables to track
- How state updates after each iteration
- Loop detection logic
- Example state transitions

**Acceptance Criteria**:
- `DecoderState` class structure defined
- All fields documented with types
- State update logic pseudocode
- Loop detection algorithm described
- Example showing state changes across 3 iterations

**Example Format**:
```python
class DecoderState:
    current_text: str
    encoding_chain: List[str]
    # ... etc
```

---

### ✅ Deliverable 6: Architecture Decision Record

**Task**: Document key decisions:
- Max iterations: 10 (with rationale)
- Stop conditions (priority order)
- Error handling strategy
- Python-controlled vs Agent-controlled loop (choice + rationale)

**Acceptance Criteria**:
- Each decision has a "Decision", "Rationale", and "Alternatives Considered" section
- At least 4 major decisions documented
- Trade-offs clearly explained

**Format**: Markdown with headings per decision

---

## Verification Checklist

Before moving to Wiki 2 (Development Environment), confirm:

- [ ] I understand why nested encodings are challenging
- [ ] I can explain the five-step iterative workflow
- [ ] I know what state variables need to be tracked
- [ ] I understand all validation metrics and their thresholds
- [ ] I can justify the max iterations limit
- [ ] I understand when to stop decoding (4+ stop conditions)
- [ ] I know the difference between Python-controlled and Agent-controlled loops
- [ ] I have created all 6 deliverables listed above
- [ ] My diagrams clearly show the iterative loop structure
- [ ] My pseudocode is detailed enough to begin coding from

---

## Next Steps

Once all deliverables are complete:

1. **Review** your architecture with the checklist above
2. **Validate** that your diagrams and pseudocode align
3. **Prepare** to implement the state management code
4. **Move to Wiki 2**: Setting up the local development environment with Docker and Ollama

---

## Summary

In this wiki, you've designed a complete architecture for an iterative CTF decoding agent:

- **Problem**: Nested encodings require intelligent, iterative decoding
- **Solution**: Five-step agent workflow with validation and state management
- **Key Components**: State manager, decoder tools, validation metrics
- **Control Strategy**: Python-controlled loop for predictability
- **Stop Conditions**: Flag found, max iterations, loop detected, no progress

You now have a solid architectural foundation to build upon in the next wikis! 🚀
