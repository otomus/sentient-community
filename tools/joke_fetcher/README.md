# joke_fetcher

Fetch random jokes from [JokeAPI](https://v2.jokeapi.dev/) — free, no API key required.

## Usage

```python
from tool import run

# Random joke from any category
print(run())

# Programming joke
print(run("Programming"))
```

## Categories

- `Any` (default)
- `Programming`
- `Misc`
- `Pun`
- `Spooky`
- `Christmas`

All jokes are filtered with safe-mode (no NSFW, religious, political, racist, or sexist content).
