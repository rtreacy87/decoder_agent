# State Module Documentation

## What is the State Module?

The State Module keeps track of everything that happens during the decoding process. It's like a notebook that records every step, every attempt, and every result so we can look back and see what worked (or didn't work).

## Where is it?

The code is in `src/state.py`.

## What does it contain?

---

## The DecoderState Class

This is the main record-keeper. It stores all information about a decoding session from start to finish.

### What it tracks:

**Core Information:**
- **current_text** — The text we're working with right now
- **original_text** — The text we started with (never changes)

**History:**
- **encoding_chain** — A list of decoder names used in order (e.g., ["base64", "hex", "rot13"])
- **text_history** — A list of every version of the text at each step

**Progress Tracking:**
- **iteration_count** — How many decoding rounds we've completed
- **max_iterations** — Maximum number of rounds allowed (usually 10)

**Status:**
- **is_complete** — True if we successfully decoded everything, False otherwise
- **completion_reason** — Why did we stop? (e.g., "Flag format detected", "max_iterations_reached")

**Metadata:**
- **confidence_scores** — How confident we were about each decoding step (list of numbers)
- **attempted_decodings** — Which decoder+text combinations we already tried (prevents repeating mistakes)

---

## Methods in DecoderState

### `__post_init__()`
**What it does:** Runs automatically when you create a new DecoderState.

**What it does specifically:** Adds the original text to the history as the first entry.

---

### `record_decode()`
**What it does:** Saves a successful decode operation.

**Parameters:**
- **encoding_type** — What decoder was used (e.g., "base64")
- **result** — The decoded text
- **confidence** — How confident we were (0.0 to 1.0)

**What it records:**
1. Adds the decoder name to the encoding chain
2. Adds the result to the text history
3. Updates current_text to the new result
4. Saves the confidence score
5. Increments the iteration counter
6. Marks this decoder+text combo as "attempted"

---

### `is_loop_detected()`
**What it does:** Checks if we're stuck going in circles.

**How it detects loops:**
1. **Exact repeat:** Current text appeared before in history
2. **No change:** Last text is the same as current text
3. **Oscillation:** We're bouncing back and forth (A→B→A→B pattern)

**Returns:** True if a loop is found, False otherwise

**Why this matters:** Prevents wasting time when decoding isn't making progress.

---

### `should_continue()`
**What it does:** Decides if we should keep decoding or stop.

**Stops when:**
1. is_complete is True (we found the answer!)
2. We hit max_iterations (tried too many times)
3. A loop is detected (we're going in circles)

**Returns:** True if we should continue, False if we should stop

---

### `to_dict()`
**What it does:** Converts all the state information into a dictionary.

**Why?** Dictionaries are easy to save, print, or send to other programs.

**What's included:**
- original_text
- final_text (current result)
- encoding_chain (list of decoders used)
- iterations (how many rounds)
- complete (True/False)
- reason (why we stopped)
- history (all text versions)
- confidence_scores
- attempted_decodings (summarized)

---

### `to_json()`
**What it does:** Converts the state to a JSON string.

**Why use this?** JSON is a standard format that can be saved to a file or shared.

**Example output:**
```json
{
  "original_text": "VGVzdA==",
  "final_text": "Test",
  "encoding_chain": ["base64"],
  "iterations": 1,
  "complete": true,
  "reason": "Natural language detected"
}
```

---

## Helper Functions

### `format_result_summary()`
**What it does:** Creates a nice, readable summary of the final results.

**Input:** A DecoderState object

**Output:** A formatted string with:
- Status (COMPLETE ✓ or INCOMPLETE)
- Reason for stopping
- Number of iterations
- Original text preview
- Final text preview
- Encoding chain (what decoders were used)
- Confidence scores

**Why use this?** When you want to show results to a human in a readable format.

**Example:**
```
======================================================================
DECODING RESULT SUMMARY
======================================================================
Status: COMPLETE ✓
Reason: Flag format detected
Iterations: 3/10

Original Text (44 chars):
  aHR0cHM6Ly9leGFtcGxlLmNvbS9mbGFne3Rlc3R9

Final Text (23 chars):
  https://example.com/flag{test}

Encoding Chain: base64 → url → rot13
Confidence Scores: ['0.95', '0.90', '0.70']
======================================================================
```

---

## How to use it

### Creating a new state:

```python
from src.state import DecoderState

# Create a new state
state = DecoderState(
    current_text="VGhpcyBpcyBhIHRlc3Q=",
    original_text="VGhpcyBpcyBhIHRlc3Q=",
    max_iterations=10
)
```

### Recording decoding steps:

```python
# After a successful decode
state.record_decode(
    encoding_type="base64",
    result="This is a test",
    confidence=0.95
)

print(f"Iteration: {state.iteration_count}")
print(f"Current text: {state.current_text}")
print(f"Encoding chain: {state.encoding_chain}")
```

### Checking if we should continue:

```python
while state.should_continue():
    # Do decoding work...
    
    # Check for loops
    if state.is_loop_detected():
        print("Loop detected!")
        break
```

### Getting the final results:

```python
# As a dictionary
results = state.to_dict()
print(results["final_text"])

# As JSON
json_str = state.to_json()
print(json_str)

# As a formatted summary
from src.state import format_result_summary
summary = format_result_summary(state)
print(summary)
```

---

## Complete example workflow:

```python
from src.state import DecoderState, format_result_summary
from src.decoders import decode_base64

# Start
state = DecoderState(
    current_text="VGhpcyBpcyBhIHRlc3Q=",
    original_text="VGhpcyBpcyBhIHRlc3Q=",
    max_iterations=10
)

# Decode
while state.should_continue():
    try:
        # Try Base64
        decoded = decode_base64(state.current_text)
        state.record_decode("base64", decoded, 0.95)
        
        # Check if we're done
        if "test" in decoded.lower():
            state.is_complete = True
            state.completion_reason = "Found expected content"
            break
            
    except Exception as e:
        state.completion_reason = f"Error: {e}"
        break

# Print results
print(format_result_summary(state))
```

---

## Tips

- Always check `should_continue()` before each iteration to avoid infinite loops
- The `attempted_decodings` set prevents trying the same decoder on the same text twice
- Loop detection catches three patterns: repeats, no-change, and oscillation
- The history keeps everything, so you can always trace back through the decoding steps
- Use `to_dict()` for programmatic access, `format_result_summary()` for human-readable output
