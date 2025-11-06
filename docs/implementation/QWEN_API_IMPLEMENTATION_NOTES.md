# Qwen API Implementation Notes

## Quick Reference

### API Key
- **Provided**: `sk-57b64160eb2f461390cfa25b2906956b`
- **Environment Variable**: `DASHSCOPE_API_KEY` or `QWEN_API_KEY`
- **Security**: Store in environment variable, NOT in code/config files

### Streaming API Details

**Protocol**: Server-Sent Events (SSE)  
**SDK**: OpenAI-compatible Python SDK  
**Documentation**: https://help.aliyun.com/zh/model-studio/stream

### Base URLs
- **Beijing Region (Default)**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **Singapore Region**: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

### Model
- **Default**: `qwen-max`
- **Token Limit**: 32,000 tokens per request

### Request Format
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

completion = client.chat.completions.create(
    model="qwen-max",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请介绍一下自己"}
    ],
    stream=True,
    stream_options={"include_usage": True}
)

# Process stream
for chunk in completion:
    if chunk.choices:
        content = chunk.choices[0].delta.content or ""
        # Process content...
    elif chunk.usage:
        # Usage info in last chunk
        print(f"Input: {chunk.usage.prompt_tokens}")
        print(f"Output: {chunk.usage.completion_tokens}")
        print(f"Total: {chunk.usage.total_tokens}")
```

### Response Format

**Each chunk contains:**
- `chunk.choices[0].delta.content` - The text content
- `chunk.usage` - Token usage (in last chunk when `include_usage=True`)

**For thinking models:**
- `chunk.choices[0].delta.reasoning_content` - Thinking process
- `chunk.choices[0].delta.content` - Final answer

### Key Implementation Points

1. **Streaming**: Always use `stream=True` for better UX
2. **Usage Tracking**: Set `stream_options={"include_usage": True}` to get token counts
3. **Token Limits**: Respect 32K token limit
4. **Error Handling**: Handle connection interruptions gracefully
5. **JSON Parsing**: Buffer stream chunks when parsing JSON responses

### Dependencies
```bash
pip install openai
```

### Environment Setup (Windows PowerShell)
```powershell
$env:DASHSCOPE_API_KEY="sk-57b64160eb2f461390cfa25b2906956b"
```

### Testing Example
```python
import os
from openai import OpenAI

# Set API key
os.environ["DASHSCOPE_API_KEY"] = "sk-57b64160eb2f461390cfa25b2906956b"

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# Test streaming
completion = client.chat.completions.create(
    model="qwen-max",
    messages=[{"role": "user", "content": "你好"}],
    stream=True,
    stream_options={"include_usage": True}
)

print("Response: ", end="", flush=True)
for chunk in completion:
    if chunk.choices:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
    elif chunk.usage:
        print(f"\n\nUsage - Input: {chunk.usage.prompt_tokens}, "
              f"Output: {chunk.usage.completion_tokens}, "
              f"Total: {chunk.usage.total_tokens}")
```

---

**Last Updated**: Based on Qwen streaming documentation as of 2025-10-29

