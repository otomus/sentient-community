# personalized_greeting

Generate personalized greetings based on the time of day. No API key required.

## Usage

```python
from tool import run

print(run())           # "Good morning! Have a great day ahead!"
print(run("Alice"))    # "Hi Alice, Good morning! Have a great day ahead!"
```

## Parameters

- `query` (string, optional): User name for personalization.
