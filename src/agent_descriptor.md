# Decoder Agent Documentation

## What is the Decoder Agent?

The Decoder Agent is a helper tool that automatically decodes text that has been hidden or scrambled using common encoding methods. Think of it like a lockpicker that tries different techniques to unlock a message. It keeps trying different decoding methods until it finds one that works, then stops when it has successfully decoded the message.

## Where is it?

The code for the Decoder Agent is found in `src/agent.py` in the `DecoderAgent` class. There's also a quick-start function called `iterative_decode` that makes it easy to use.

## How to set it up

When you create a new Decoder Agent, you can give it a few options:

- **max_iterations** (default: 10) — How many times should the agent try to decode? Each try is one "iteration." If it hasn't figured it out after 10 tries, it gives up.
- **verbose** (default: False) — Should the agent tell you what it's doing step-by-step? Set this to `True` if you want to see all the details as it works, or `False` if you just want the final answer.

Example: `agent = DecoderAgent(max_iterations=10, verbose=True)`

## What the agent does (step by step)

### Main Method: `decode()`

The `decode()` method is the main entry point. You give it a scrambled message, and it returns the decoded result.

**What it does:**
1. Takes your scrambled text as input
2. Runs the decoding loop multiple times (up to max_iterations)
3. Returns a report with the final result and what it learned along the way

---

## The Helper Methods (what happens inside)

### `_log()` 
**What it does:** Prints status messages to the screen.
- If `verbose=True`, it shows every step the agent takes
- If `verbose=False`, it stays silent
- Useful for debugging or seeing progress

### `_select_decoder()` 
**What it does:** Chooses which decoding method to try next.
- Looks at the scrambled text and analyzes its patterns
- Rates different decoding methods by confidence (how sure it is that method will work)
- Picks the method with the highest confidence score
- Only picks methods with confidence above 30% (30% sure)
- Returns the chosen method and its confidence score

### `_apply_decoder()`
**What it does:** Actually tries to decode the text using a specific method.
- Takes a decoder name (like "base64" or "hex") and the scrambled text
- Runs that decoder on the text
- If it works, returns `True` and the decoded text
- If it fails, returns `False` and the original text unchanged
- Catches any errors that happen

### `_try_alternative_decoders()`
**What it does:** If the first chosen decoder doesn't work, try others.
- Used as a backup plan when the recommended decoder fails
- Tries all available decoders until one succeeds
- Returns the first one that works, along with a confidence score of 0.7 (70%)

### `decode_iteration()`
**What it does:** Runs one complete "round" of decoding.
- **Step 1:** Analyzes the text (looks at patterns, how random it is, how many readable characters)
- **Step 2:** Guesses which decoding method will work best
- **Step 3:** Tries the selected decoder
- **Step 4:** Checks if the result looks correct (is it readable? Does it look like a real message?)
- **Step 5:** Decides whether to try again or stop

**Decision logic:**
- If the result looks like a complete, real message → **STOP** (we're done!)
- If the result failed completely → **STOP** (give up)
- If we detect we're going in circles (decoding the same thing repeatedly) → **STOP**
- Otherwise → **CONTINUE** to the next iteration

---

## Quick Start Function: `iterative_decode()`

This is a shortcut function that makes the decoder super easy to use. Instead of creating an agent object yourself, you can just call this one function.

**What it does:**
- Creates a DecoderAgent for you automatically
- Runs the decoding process
- Returns the results

**Parameters:**
- **encoded_text** — The scrambled message you want to decode
- **max_iterations** (default: 10) — How many times to try decoding
- **verbose** (default: True) — Whether to show progress (note: defaults to True, unlike the agent which defaults to False)

**Why use this?**
It's simpler! You don't need to create an agent object first. Just one function call and you're done.

---

## How to use it

```python
from src.agent import DecoderAgent, iterative_decode

# Option 1: Use the quick function (easiest!)
result = iterative_decode("VGhpcyBpcyBhIHRlc3Q=", max_iterations=10, verbose=True)
print(result)

# Option 2: Create an agent and use it directly (more control)
agent = DecoderAgent(max_iterations=10, verbose=True)
result = agent.decode("VGhpcyBpcyBhIHRlc3Q=")
print(result)
```

## The result

When the agent finishes, it gives you a dictionary with:
- **success**: True or False (did it successfully decode?)
- **current_text**: The final decoded text
- **original_text**: What you started with
- **decode_log**: A list of all the decoding steps it tried
- **completion_reason**: Why it stopped (found answer, no progress, loop detected, etc.)

## Tips for using it

- Use `verbose=True` when debugging to see what the agent is doing
- The agent works best with text that has been encoded once or twice (not 5 times in a row)
- If it seems stuck, you might have text encoded in an unusual way that the agent doesn't recognize
