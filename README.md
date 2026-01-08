# Luna plugin for LiveKit Agents

Support for [Luna Hindi TTS](https://hindi.heypixa.ai/) in LiveKit Agents.

Luna TTS provides high-quality Hindi text-to-speech synthesis with real-time streaming.

## Installation

```bash
pip install livekit-plugins-luna
```

## Usage

```python
from livekit.agents import AgentSession
from livekit.plugins.luna import TTS

session = AgentSession(
    tts=TTS(),
)
```

## Features

- Real-time streaming via SSE and WebSocket
- PCM16 audio at 32kHz sample rate
- Low latency (~300ms)
- Configurable sampling parameters (top_p, repetition_penalty)

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | `https://hindi.heypixa.ai` | Luna TTS API base URL |
| `top_p` | float | `0.95` | Top-p sampling (0.0-1.0) |
| `repetition_penalty` | float | `1.3` | Repetition penalty (1.0-2.0) |

## API Documentation

See the [Luna TTS API Documentation](https://hindi.heypixa.ai/docs) for more details.
