---
name: delegate-to-ollama
description: Delegate a self-contained coding task to the local Ollama qwen2.5:7b model via curl, then review and apply the result. Use when the user types /delegate-to-ollama, or when running /tdd and the user says to delegate implementation to Ollama.
---

# Delegate to Ollama

Offload a well-scoped coding task to `qwen2.5:7b` running locally, then review and apply the output.

## When to use

- User types `/delegate-to-ollama <task>`
- During `/tdd` GREEN phase: user says "delegate this to Ollama" after a failing test exists

## Steps

### 1. Scope the task

Before calling Ollama, confirm the task is self-contained:
- [ ] Inputs and outputs are fully defined
- [ ] No external state beyond what can be described in the prompt
- [ ] Expected behavior is clear (ideally a failing test already exists)

If scoping is unclear, ask the user one question to sharpen it.

### 2. Build the prompt

Construct a prompt that includes:
- The function/class signature to implement
- The test(s) it must pass (paste them verbatim if they exist)
- Any type hints, domain constraints, or existing interfaces it must conform to
- "Return only the implementation code, no explanation."

### 3. Call Ollama

```bash
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "prompt": "<your prompt here>",
    "stream": false
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

Use the Bash tool to run this. Escape the prompt JSON carefully — use a Python heredoc approach if the prompt contains quotes:

```bash
python3 -c "
import subprocess, json, sys
prompt = '''<multi-line prompt here>'''
payload = json.dumps({'model': 'qwen2.5:7b', 'prompt': prompt, 'stream': False})
result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/generate',
    '-H', 'Content-Type: application/json', '-d', payload],
    capture_output=True, text=True)
print(json.loads(result.stdout)['response'])
"
```

### 4. Review the output

Before applying:
- [ ] Code compiles / is syntactically valid Python
- [ ] It matches the expected signature
- [ ] It does not introduce security issues (no shell injection, no hardcoded secrets)
- [ ] It does not silently swallow exceptions

If the output is wrong or incomplete, revise the prompt and retry once. If it fails again, implement it yourself.

### 5. Apply and verify

- Paste the implementation into the target file using the Edit tool
- Run the tests: `cd backend && pytest tests/ -v`
- If tests pass → done. If not → fix the gap yourself (do not loop Ollama indefinitely)

## Completion criterion

Tests that were RED before the delegation are now GREEN, and the implementation has been reviewed for correctness and safety.
