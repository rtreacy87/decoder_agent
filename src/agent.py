"""
Main iterative CTF decoder agent.

This module implements the core agent logic that orchestrates
the iterative decoding workflow.
"""

from typing import Dict, Optional, Tuple
import traceback

from .state import DecoderState, format_result_summary
from .decoders import (
    decode_base64, decode_hex, decode_rot13, decode_url, 
    DecoderError, try_all_decoders
)
from .analysis import (
    analyze_encoding_characteristics, 
    identify_likely_encoding,
    validate_decoded_result,
    print_analysis
)


class DecoderAgent:
    """
    Iterative CTF decoder agent.
    
    This agent performs iterative decoding of nested encodings
    commonly found in CTF challenges.
    """
    
    def __init__(self, max_iterations: int = 10, verbose: bool = False):
        """
        Initialize the decoder agent.
        
        Args:
            max_iterations: Maximum number of decoding iterations
            verbose: Whether to print detailed progress information
        """
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.decoders = {
            "base64": decode_base64,
            "hex": decode_hex,
            "rot13": decode_rot13,
            "url": decode_url,
        }
    
    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def _select_decoder(self, analysis, confidence_scores: Dict[str, float]) -> Tuple[Optional[str], float]:
        """
        Select the most likely decoder based on analysis.
        
        Args:
            analysis: TextAnalysis object
            confidence_scores: Confidence scores for each decoder
            
        Returns:
            Tuple of (decoder_name, confidence_score) or (None, 0.0)
        """
        # Sort by confidence
        sorted_decoders = sorted(
            confidence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for decoder_name, confidence in sorted_decoders:
            if confidence > 0.3:  # Minimum confidence threshold
                return decoder_name, confidence
        
        return None, 0.0
    
    def _apply_decoder(self, decoder_name: str, text: str) -> Tuple[bool, str]:
        """
        Apply a decoder to the text.
        
        Args:
            decoder_name: Name of the decoder to apply
            text: Text to decode
            
        Returns:
            Tuple of (success, result_text)
        """
        if decoder_name not in self.decoders:
            return False, text
        
        try:
            decoder_func = self.decoders[decoder_name]
            result = decoder_func(text)
            return True, result
        except DecoderError as e:
            self._log(f"  Decoder '{decoder_name}' failed: {e}")
            return False, text
    
    def _try_alternative_decoders(self, text: str) -> Optional[Tuple[str, str, float]]:
        """
        Try alternative decoders to find one that works.
        
        Args:
            text: Text to decode
            
        Returns:
            Tuple of (decoder_name, decoded_text, confidence) or None
        """
        self._log(f"  Trying alternative decoders...")
        
        results = try_all_decoders(text)
        
        if results:
            # Return the first successful decode
            decoder_name, decoded_text = results[0]
            self._log(f"  Alternative decoder '{decoder_name}' succeeded")
            return decoder_name, decoded_text, 0.7
        
        return None
    
    def decode_iteration(self, state: DecoderState) -> bool:
        """
        Perform a single decoding iteration.
        
        Args:
            state: Current decoder state
            
        Returns:
            True if decoding should continue, False if complete/failed
        """
        self._log(f"\n--- Iteration {state.iteration_count + 1} ---")
        self._log(f"Current text: {state.current_text[:60]}...")
        
        # Step 1: Analyze text characteristics
        self._log("Step 1: Analyzing text characteristics...")
        analysis = analyze_encoding_characteristics(state.current_text)
        
        self._log(f"  Charset: {analysis.charset}")
        self._log(f"  Length: {analysis.length}")
        self._log(f"  Entropy: {analysis.entropy:.2f}")
        self._log(f"  Printable ratio: {analysis.printable_ratio:.2%}")
        
        # Step 2: Identify likely encoding
        self._log("Step 2: Identifying likely encoding...")
        confidence_scores = identify_likely_encoding(analysis)
        
        decoder_name, confidence = self._select_decoder(analysis, confidence_scores)
        
        if decoder_name is None:
            self._log("  No suitable decoder found")
            return False
        
        self._log(f"  Selected decoder: '{decoder_name}' (confidence: {confidence:.2f})")
        
        # Step 3: Apply decoder
        self._log(f"Step 3: Applying '{decoder_name}' decoder...")
        success, decoded_text = self._apply_decoder(decoder_name, state.current_text)
        
        if not success or decoded_text == state.current_text:
            # Try alternatives
            alt_result = self._try_alternative_decoders(state.current_text)
            if alt_result:
                decoder_name, decoded_text, confidence = alt_result
                success = True
            else:
                self._log("  All decoders failed")
                return False
        else:
            self._log(f"  Decode succeeded: {decoded_text[:60]}...")
        
        # Step 4: Validate result
        self._log("Step 4: Validating result...")
        validation = validate_decoded_result(state.current_text, decoded_text)
        
        self._log(f"  Validation status: {validation['status']}")
        self._log(f"  Reason: {validation['reason']}")
        self._log(f"  Confidence: {validation['confidence']:.2f}")
        
        # Record the decode
        state.record_decode(decoder_name, decoded_text, confidence)
        
        # Step 5: Decision point
        self._log("Step 5: Decision point...")
        
        if validation["status"] == "COMPLETE":
            self._log("  Status: COMPLETE - Stopping iteration")
            state.is_complete = True
            state.completion_reason = validation["reason"]
            return False
        
        if validation["status"] == "FAILED":
            self._log("  Status: FAILED - No progress made")
            state.completion_reason = "no_progress"
            return False
        
        # Check for loops
        if state.is_loop_detected():
            self._log("  Loop detected - Stopping iteration")
            state.completion_reason = "loop_detected"
            return False
        
        # Continue with partial result
        self._log("  Status: PARTIAL - Continuing iteration")
        state.current_text = decoded_text
        return True
    
    def decode(self, encoded_text: str) -> Dict:
        """
        Perform iterative decoding on the given text.
        
        Args:
            encoded_text: The text to decode
            
        Returns:
            Dictionary with decoding results
        """
        self._log(f"\nStarting iterative decoding...")
        self._log(f"Input text: {encoded_text[:60]}...")
        
        # Initialize state
        state = DecoderState(
            current_text=encoded_text,
            original_text=encoded_text,
            max_iterations=self.max_iterations
        )
        
        # Main decoding loop
        try:
            while state.should_continue():
                # Perform one iteration
                should_continue = self.decode_iteration(state)
                
                if not should_continue:
                    break
        
        except Exception as e:
            self._log(f"\nError during decoding: {e}")
            if self.verbose:
                traceback.print_exc()
            state.completion_reason = f"error: {str(e)}"
        
        # Format and return results
        results = state.to_dict()
        results["success"] = state.is_complete
        
        if self.verbose:
            print("\n" + format_result_summary(state))
        
        return results


def iterative_decode(
    encoded_text: str,
    max_iterations: int = 10,
    verbose: bool = True
) -> Dict:
    """
    Decode a text iteratively.
    
    This is a convenience function that creates an agent and runs decoding.
    
    Args:
        encoded_text: The text to decode
        max_iterations: Maximum number of iterations
        verbose: Whether to print progress information
        
    Returns:
        Dictionary with decoding results
    """
    agent = DecoderAgent(max_iterations=max_iterations, verbose=verbose)
    return agent.decode(encoded_text)
