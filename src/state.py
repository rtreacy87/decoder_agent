"""
State management for the iterative CTF decoder agent.

This module handles tracking the decoding progress, maintaining history,
and detecting loops or stop conditions.
"""

from typing import List, Set, Tuple, Optional
from dataclasses import dataclass, field, asdict
import json


@dataclass
class DecoderState:
    """State management for iterative decoding."""
    
    # Core state
    current_text: str
    original_text: str
    
    # History tracking
    encoding_chain: List[str] = field(default_factory=list)
    text_history: List[str] = field(default_factory=list)
    
    # Loop control
    iteration_count: int = 0
    max_iterations: int = 10
    
    # Status
    is_complete: bool = False
    completion_reason: str = ""
    
    # Metadata
    confidence_scores: List[float] = field(default_factory=list)
    attempted_decodings: Set[Tuple[str, str]] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize history with original text."""
        self.text_history = [self.original_text]
    
    def record_decode(self, encoding_type: str, result: str, confidence: float) -> None:
        """
        Record a successful decode operation.
        
        Args:
            encoding_type: The type of encoding that was applied (e.g., "base64", "hex")
            result: The decoded text result
            confidence: Confidence level of the decode (0.0-1.0)
        """
        self.encoding_chain.append(encoding_type)
        self.text_history.append(result)
        self.current_text = result
        self.confidence_scores.append(confidence)
        self.iteration_count += 1
        
        # Mark this attempt as tried
        if len(self.text_history) > 1:
            self.attempted_decodings.add((self.text_history[-2], encoding_type))
    
    def is_loop_detected(self) -> bool:
        """
        Detect if we're in a decoding loop.
        
        Returns:
            True if a loop is detected, False otherwise
        """
        # Check if current text appeared before
        if self.current_text in self.text_history[:-1]:
            return True
        
        # Check if we're trying the same decoder on the same text
        if len(self.text_history) > 1:
            last_text = self.text_history[-2]
            if last_text == self.current_text:
                return True
        
        # Check for oscillation (A→B→A→B pattern)
        if len(self.text_history) >= 4:
            if (self.text_history[-1] == self.text_history[-3] and 
                self.text_history[-2] == self.text_history[-4]):
                return True
        
        return False
    
    def should_continue(self) -> bool:
        """
        Determine if decoding should continue.
        
        Returns:
            True if decoding should continue, False if it should stop
        """
        if self.is_complete:
            return False
        if self.iteration_count >= self.max_iterations:
            self.completion_reason = "max_iterations_reached"
            return False
        if self.is_loop_detected():
            self.completion_reason = "loop_detected"
            return False
        return True
    
    def to_dict(self) -> dict:
        """
        Export state as dictionary for serialization.
        
        Returns:
            Dictionary representation of the state
        """
        # Convert attempted_decodings set to list of tuples for serialization
        attempted_decodings_list = [
            {"text_snippet": text[:50], "decoder": decoder}
            for text, decoder in self.attempted_decodings
        ]
        
        return {
            "original_text": self.original_text,
            "final_text": self.current_text,
            "encoding_chain": self.encoding_chain,
            "iterations": self.iteration_count,
            "complete": self.is_complete,
            "reason": self.completion_reason,
            "history": self.text_history,
            "confidence_scores": self.confidence_scores,
            "attempted_decodings": attempted_decodings_list
        }
    
    def to_json(self) -> str:
        """
        Export state as JSON string.
        
        Returns:
            JSON string representation of the state
        """
        return json.dumps(self.to_dict(), indent=2)


def format_result_summary(state: DecoderState) -> str:
    """
    Format the decoding result as a readable summary.
    
    Args:
        state: The final decoder state
        
    Returns:
        Formatted string summary of results
    """
    lines = [
        "=" * 70,
        "DECODING RESULT SUMMARY",
        "=" * 70,
        f"Status: {'COMPLETE ✓' if state.is_complete else 'INCOMPLETE'}",
        f"Reason: {state.completion_reason}",
        f"Iterations: {state.iteration_count}/{state.max_iterations}",
        "",
        f"Original Text ({len(state.original_text)} chars):",
        f"  {state.original_text[:100]}{'...' if len(state.original_text) > 100 else ''}",
        "",
        f"Final Text ({len(state.current_text)} chars):",
        f"  {state.current_text[:100]}{'...' if len(state.current_text) > 100 else ''}",
        "",
        f"Encoding Chain: {' → '.join(state.encoding_chain) if state.encoding_chain else 'None'}",
        f"Confidence Scores: {[f'{c:.2f}' for c in state.confidence_scores]}",
        "=" * 70,
    ]
    
    return "\n".join(lines)
