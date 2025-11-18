"""Streaming JSON parser for real-time JSON parsing from token streams."""

import json
import re
from typing import Dict, Any, Optional, Callable, List


class StreamingJSONParser:
    """
    Parser that can extract and parse JSON objects incrementally from a token stream.
    
    This parser handles:
    - Partial JSON as it arrives
    - Multiple JSON objects in a stream
    - Extra data after valid JSON
    - Real-time updates as JSON fields are completed
    """
    
    def __init__(self, on_update: Optional[Callable[[Dict[str, Any], bool], None]] = None):
        """
        Initialize streaming JSON parser.
        
        Args:
            on_update: Optional callback function that receives (parsed_data, is_complete) 
                      when JSON fields are updated. is_complete=True when a complete JSON object is parsed.
        """
        self.buffer = ""
        self.parsed_data: Dict[str, Any] = {}
        self.last_parsed_data: Dict[str, Any] = {}
        self.on_update = on_update
        self.json_started = False
        self.brace_count = 0
        self.in_string = False
        self.escape_next = False
        
    def feed(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Feed a token to the parser and return parsed data if available.
        
        Args:
            token: Token string to add to the buffer
            
        Returns:
            Parsed JSON dict if a complete object is available, None otherwise.
            Also calls on_update callback with partial data as fields are completed.
        """
        self.buffer += token
        
        # Try to find JSON start
        if not self.json_started:
            start_idx = self.buffer.find("{")
            if start_idx >= 0:
                self.buffer = self.buffer[start_idx:]
                self.json_started = True
                self.brace_count = 0
            else:
                return None
        
        if not self.json_started:
            return None
        
        # Update state tracking
        self._update_state()
        
        # Always try to extract partial JSON first (for real-time updates)
        # This allows us to show data as it arrives, even if JSON is incomplete
        try:
            partial = self._extract_partial_json()
            if partial and partial != self.last_parsed_data:
                self.parsed_data = partial
                self.last_parsed_data = partial.copy()
                if self.on_update:
                    self.on_update(partial, False)
        except Exception:
            pass  # Ignore errors in partial extraction
        
        # Try to extract complete JSON when braces are balanced
        if self.brace_count == 0 and self.json_started:
            try:
                # Find the end of the first complete JSON object
                json_end = self._find_json_end()
                if json_end > 0:
                    json_str = self.buffer[:json_end + 1]
                    parsed = json.loads(json_str)
                    
                    # Check if this is new data
                    if parsed != self.last_parsed_data:
                        self.parsed_data = parsed
                        self.last_parsed_data = parsed.copy()
                        
                        # Call update callback with complete flag
                        if self.on_update:
                            self.on_update(parsed, True)
                        
                        return parsed
            except (json.JSONDecodeError, ValueError, IndexError):
                pass  # Partial extraction already handled above
        
        return None
    
    def _update_state(self):
        """Update internal state tracking for braces and strings."""
        self.brace_count = 0
        self.in_string = False
        self.escape_next = False
        
        for char in self.buffer:
            if self.escape_next:
                self.escape_next = False
                continue
            
            if char == '\\':
                self.escape_next = True
                continue
            
            if char == '"' and not self.escape_next:
                self.in_string = not self.in_string
                continue
            
            if not self.in_string:
                if char == '{':
                    self.brace_count += 1
                elif char == '}':
                    self.brace_count -= 1
    
    def _find_json_end(self) -> int:
        """Find the end position of the first complete JSON object."""
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(self.buffer):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i
        
        return -1
    
    def _extract_partial_json(self) -> Optional[Dict[str, Any]]:
        """
        Try to extract partial JSON data from the buffer.
        This attempts to parse what we have so far, handling incomplete values.
        """
        try:
            partial = {}
            
            # Strategy 1: Try to find complete key-value pairs with string values
            # Pattern: "key": "complete_string_value"
            string_pattern = r'"([^"]+)":\s*"([^"]*)"'
            for match in re.finditer(string_pattern, self.buffer):
                key = match.group(1)
                value = match.group(2)
                # Only add if we haven't seen this key yet or if it's more complete
                if key not in partial or isinstance(partial[key], str):
                    partial[key] = value
            
            # Strategy 2: Try to find complete key-value pairs with numeric/boolean/null values
            # Pattern: "key": number, "key": true, "key": false, "key": null
            simple_value_pattern = r'"([^"]+)":\s*(true|false|null|\d+\.?\d*)'
            for match in re.finditer(simple_value_pattern, self.buffer):
                key = match.group(1)
                value_str = match.group(2)
                try:
                    if value_str == "true":
                        value = True
                    elif value_str == "false":
                        value = False
                    elif value_str == "null":
                        value = None
                    else:
                        value = float(value_str) if '.' in value_str else int(value_str)
                    partial[key] = value
                except (ValueError, TypeError):
                    pass
            
            # Strategy 3: Try to extract array items (for arrays of objects)
            # Look for "key": [ and try to extract complete objects within
            array_start_pattern = r'"([^"]+)":\s*\['
            for match in re.finditer(array_start_pattern, self.buffer):
                key = match.group(1)
                start_pos = match.end()
                
                # Find the content between [ and ]
                brace_count = 0
                in_string = False
                escape_next = False
                items = []
                current_item_start = start_pos
                
                i = start_pos
                while i < len(self.buffer):
                    char = self.buffer[i]
                    
                    if escape_next:
                        escape_next = False
                        i += 1
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        i += 1
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        i += 1
                        continue
                    
                    if not in_string:
                        if char == '{':
                            if brace_count == 0:
                                current_item_start = i
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # Found a complete object
                                item_str = self.buffer[current_item_start:i+1]
                                try:
                                    item = json.loads(item_str)
                                    items.append(item)
                                except (json.JSONDecodeError, ValueError):
                                    pass
                        elif char == ']' and brace_count == 0:
                            # End of array
                            break
                    
                    i += 1
                
                if items:
                    partial[key] = items
            
            return partial if partial else None
            
        except Exception:
            return None
    
    def get_current_data(self) -> Dict[str, Any]:
        """Get the most recently parsed data (may be partial)."""
        return self.parsed_data.copy()
    
    def reset(self):
        """Reset the parser state."""
        self.buffer = ""
        self.parsed_data = {}
        self.last_parsed_data = {}
        self.json_started = False
        self.brace_count = 0
        self.in_string = False
        self.escape_next = False

