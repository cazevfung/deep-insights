import json
import os
from pathlib import Path
from collections import OrderedDict

def remove_duplicate_questions(conversation_file):
    """Remove duplicate questions from a conversation file, keeping only the earliest occurrence."""
    
    with open(conversation_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'messages' not in data or not data['messages']:
        print(f"No messages found in {conversation_file}")
        return 0
    
    messages = data['messages']
    seen_questions = {}  # question_content -> (first_index, first_created_at)
    indices_to_remove = set()
    
    # First pass: identify duplicates
    for i, message in enumerate(messages):
        if message.get('role') == 'user':
            question_content = message.get('content', '').strip()
            created_at = message.get('created_at', '')
            
            if question_content:
                if question_content in seen_questions:
                    # This is a duplicate - check if we should remove it
                    first_index, first_created_at = seen_questions[question_content]
                    
                    # Keep the earliest one (by created_at timestamp)
                    if created_at < first_created_at:
                        # Current one is earlier, mark the previous one for removal
                        indices_to_remove.add(first_index)
                        # Also remove its answer if it exists
                        if first_index + 1 < len(messages) and messages[first_index + 1].get('role') == 'assistant':
                            indices_to_remove.add(first_index + 1)
                        # Update seen_questions with the earlier one
                        seen_questions[question_content] = (i, created_at)
                    else:
                        # Previous one is earlier, mark current one and its answer for removal
                        indices_to_remove.add(i)
                        if i + 1 < len(messages) and messages[i + 1].get('role') == 'assistant':
                            indices_to_remove.add(i + 1)
                else:
                    # First time seeing this question
                    seen_questions[question_content] = (i, created_at)
    
    # Second pass: also identify assistant messages that reply to removed user messages
    for i, message in enumerate(messages):
        if message.get('role') == 'assistant':
            in_reply_to = message.get('metadata', {}).get('in_reply_to')
            if in_reply_to:
                # Find the user message this replies to
                for j in range(i - 1, -1, -1):
                    if messages[j].get('id') == in_reply_to:
                        if j in indices_to_remove:
                            indices_to_remove.add(i)
                        break
    
    # Remove duplicates (in reverse order to maintain indices)
    removed_count = len(indices_to_remove)
    for i in sorted(indices_to_remove, reverse=True):
        messages.pop(i)
    
    data['messages'] = messages
    
    # Write back to file
    with open(conversation_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return removed_count

def main():
    # Get project root (two levels up from scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    conversations_dir = project_root / "data" / "research" / "conversations"
    
    if not conversations_dir.exists():
        print(f"Directory not found: {conversations_dir}")
        return
    
    conversation_files = list(conversations_dir.glob("*.json"))
    
    if not conversation_files:
        print("No conversation files found")
        return
    
    total_removed = 0
    for conv_file in conversation_files:
        print(f"\nProcessing {conv_file.name}...")
        removed = remove_duplicate_questions(conv_file)
        total_removed += removed
        if removed > 0:
            print(f"  Removed {removed} duplicate message(s)")
        else:
            print(f"  No duplicates found")
    
    print(f"\n=== Summary ===")
    print(f"Total messages removed: {total_removed}")

if __name__ == "__main__":
    main()

