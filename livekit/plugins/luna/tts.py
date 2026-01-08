# Copyright 2024 HeyPixa
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Luna Hindi TTS Plugin for LiveKit Agents

This plugin provides integration with the Luna Hindi Text-to-Speech API
(https://hindi.heypixa.ai) for real-time Hindi speech synthesis.

The API supports:
- Real-time streaming via Server-Sent Events (SSE)
- WebSocket streaming for bidirectional communication
- PCM16 audio at 32kHz sample rate
- Low latency (~300ms)
"""

from __future__ import annotations

import asyncio
import base64
import json
import weakref
from dataclasses import dataclass, replace

import aiohttp

from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIError,
    APIStatusError,
    APITimeoutError,
    tts,
    utils,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

from .log import logger

# Luna TTS API constants
DEFAULT_BASE_URL = "https://hindi.heypixa.ai"
SAMPLE_RATE = 32000
NUM_CHANNELS = 1
MAX_TEXT_LENGTH = 5000  # Maximum characters per request

# Default sampling parameters (from API docs)
DEFAULT_TOP_P = 0.95
DEFAULT_REPETITION_PENALTY = 1.3


@dataclass
class TTSConfig:
    """Configuration returned by the Luna TTS API."""

    sample_rate: int
    top_p: float
    repetition_penalty: float


@dataclass
class HealthStatus:
    """Health status returned by the Luna TTS API."""

    status: str
    timestamp: str
    backend_status: str
    voice_cloning: bool = False


@dataclass
class _TTSOptions:
    """Configuration options for Luna TTS."""

    base_url: str
    top_p: float
    repetition_penalty: float

    def get_http_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_ws_url(self, path: str) -> str:
        return f"{self.base_url.replace('http', 'ws', 1)}{path}"


class TTS(tts.TTS):
    """
    Luna Hindi Text-to-Speech implementation for LiveKit Agents.

    This TTS provider uses the Luna API (hindi.heypixa.ai) to synthesize
    high-quality Hindi speech with real-time streaming.

    Example usage:
        ```python
        from livekit.agents import AgentSession
        from livekit.plugins.luna import TTS

        session = AgentSession(
            tts=TTS(),
            # ... other config
        )
        ```

    API Documentation: https://hindi.heypixa.ai/docs
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        top_p: float = DEFAULT_TOP_P,
        repetition_penalty: float = DEFAULT_REPETITION_PENALTY,
        http_session: aiohttp.ClientSession | None = None,
    ) -> None:
        """
        Create a new instance of Luna Hindi TTS.

        Args:
            base_url: The base URL for the Luna TTS API.
                      Defaults to "https://hindi.heypixa.ai".
            top_p: Top-p (nucleus) sampling parameter (0.0-1.0).
                   Higher values make output more diverse. Defaults to 0.95.
            repetition_penalty: Penalty for repeating tokens (1.0-2.0).
                               Higher values reduce repetition. Defaults to 1.3.
            http_session: Optional aiohttp ClientSession to reuse.
                         If not provided, a new session will be created.
        """
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=True,
                aligned_transcript=False,  # Luna doesn't provide word timestamps
            ),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )

        self._opts = _TTSOptions(
            base_url=base_url,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
        )

        self._session = http_session
        self._streams = weakref.WeakSet[SynthesizeStream]()

    @property
    def model(self) -> str:
        return "luna"

    @property
    def provider(self) -> str:
        return "heypixa"

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = utils.http_context.http_session()
        return self._session

    async def get_config(self) -> TTSConfig:
        """
        Get the current API configuration from the server.

        Returns:
            TTSConfig with sample_rate and default sampling parameters.

        Raises:
            APIConnectionError: If the request fails.
        """
        session = self._ensure_session()
        url = self._opts.get_http_url("/api/v1/config")

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise APIStatusError(
                        f"Failed to get config: {response.status}",
                        status_code=response.status,
                        request_id="",
                        body=await response.text(),
                    )
                data = await response.json()
                defaults = data.get("sampling_defaults", {})
                return TTSConfig(
                    sample_rate=data.get("sample_rate", SAMPLE_RATE),
                    top_p=defaults.get("top_p", DEFAULT_TOP_P),
                    repetition_penalty=defaults.get("repetition_penalty", DEFAULT_REPETITION_PENALTY),
                )
        except aiohttp.ClientError as e:
            raise APIConnectionError(str(e)) from e

    async def check_health(self) -> HealthStatus:
        """
        Check the health status of the Luna TTS API.

        Returns:
            HealthStatus with status, timestamp, and backend information.

        Raises:
            APIConnectionError: If the request fails.
        """
        session = self._ensure_session()
        url = self._opts.get_http_url("/api/v1/health")

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise APIStatusError(
                        f"Health check failed: {response.status}",
                        status_code=response.status,
                        request_id="",
                        body=await response.text(),
                    )
                data = await response.json()
                return HealthStatus(
                    status=data.get("status", "unknown"),
                    timestamp=data.get("timestamp", ""),
                    backend_status=data.get("backend_status", "unknown"),
                    voice_cloning=data.get("voice_cloning", False),
                )
        except aiohttp.ClientError as e:
            raise APIConnectionError(str(e)) from e

    def update_options(
        self,
        *,
        top_p: float | None = None,
        repetition_penalty: float | None = None,
    ) -> None:
        """
        Update the TTS configuration options.

        Args:
            top_p: Top-p sampling parameter (0.0-1.0).
            repetition_penalty: Repetition penalty (1.0-2.0).
        """
        if top_p is not None:
            self._opts.top_p = top_p
        if repetition_penalty is not None:
            self._opts.repetition_penalty = repetition_penalty

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> ChunkedStream:
        """
        Synthesize speech from text using the HTTP SSE endpoint.

        This method uses the POST /api/v1/synthesize endpoint which streams
        audio chunks via Server-Sent Events.

        Args:
            text: The Hindi text to synthesize (max 5000 chars).
                  Use natural punctuation (।, ?, !) for best results.
            conn_options: Connection options for retry behavior.

        Returns:
            A ChunkedStream that yields SynthesizedAudio frames.

        Raises:
            ValueError: If text exceeds MAX_TEXT_LENGTH (5000 chars).
        """
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(
                f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters "
                f"(got {len(text)} chars). Split your text into smaller chunks."
            )
        return ChunkedStream(tts=self, input_text=text, conn_options=conn_options)

    def stream(
        self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> SynthesizeStream:
        """
        Create a streaming synthesis session using WebSocket.

        This allows streaming text chunks in real-time and receiving
        audio chunks as they're generated.

        Args:
            conn_options: Connection options for retry behavior.

        Returns:
            A SynthesizeStream for bidirectional streaming.
        """
        stream = SynthesizeStream(tts=self, conn_options=conn_options)
        self._streams.add(stream)
        return stream

    async def aclose(self) -> None:
        """Close all active streams."""
        for stream in list(self._streams):
            await stream.aclose()
        self._streams.clear()


class ChunkedStream(tts.ChunkedStream):
    """
    Non-streaming TTS using HTTP SSE endpoint.

    This uses the POST /api/v1/synthesize endpoint which returns
    audio chunks via Server-Sent Events.
    """

    def __init__(
        self,
        *,
        tts: TTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts: TTS = tts
        self._opts = replace(tts._opts)

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        """Execute the TTS request and emit audio frames."""
        session = self._tts._ensure_session()
        url = self._opts.get_http_url("/api/v1/synthesize")

        request_body = {
            "text": self.input_text,
            "top_p": self._opts.top_p,
            "repetition_penalty": self._opts.repetition_penalty,
        }

        try:
            async with session.post(
                url,
                json=request_body,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(
                    total=None,  # No total timeout for streaming
                    connect=self._conn_options.timeout,
                    sock_read=30.0,  # 30 second read timeout per chunk
                ),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIStatusError(
                        f"Luna TTS API error: {error_text}",
                        status_code=response.status,
                        request_id=response.headers.get("x-request-id", ""),
                        body=error_text,
                    )

                # Initialize the emitter for raw PCM audio
                request_id = response.headers.get("x-request-id", utils.shortuuid())
                output_emitter.initialize(
                    request_id=request_id,
                    sample_rate=SAMPLE_RATE,
                    num_channels=NUM_CHANNELS,
                    mime_type="audio/pcm",  # Raw PCM16 little-endian
                )

                # Process SSE stream
                buffer = ""
                async for chunk in response.content.iter_any():
                    if not chunk:
                        continue

                    buffer += chunk.decode("utf-8")

                    # Process complete SSE events
                    while "\n\n" in buffer:
                        event, buffer = buffer.split("\n\n", 1)

                        for line in event.split("\n"):
                            if line.startswith("data: "):
                                data = line[6:]  # Remove "data: " prefix

                                if data == "[DONE]":
                                    # End of stream
                                    output_emitter.flush()
                                    return

                                try:
                                    obj = json.loads(data)
                                    if "audio" in obj:
                                        # Decode base64 audio and push
                                        audio_bytes = base64.b64decode(obj["audio"])
                                        output_emitter.push(audio_bytes)
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse SSE data: {e}")
                                    continue

                output_emitter.flush()

        except asyncio.TimeoutError:
            raise APITimeoutError() from None
        except aiohttp.ClientError as e:
            raise APIConnectionError(str(e)) from e


class SynthesizeStream(tts.SynthesizeStream):
    """
    Streaming TTS using WebSocket endpoint.

    This uses the WS /api/v1/ws/synthesize endpoint for bidirectional
    streaming of text input and audio output.
    """

    def __init__(
        self,
        *,
        tts: TTS,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts, conn_options=conn_options)
        self._tts: TTS = tts
        self._opts = replace(tts._opts)

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        """Execute the WebSocket TTS session."""
        session = self._tts._ensure_session()
        ws_url = self._opts.get_ws_url("/api/v1/ws/synthesize")
        request_id = utils.shortuuid()

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
            stream=True,
        )

        segment_id = utils.shortuuid()
        text_buffer = ""

        try:
            async with session.ws_connect(
                ws_url,
                timeout=aiohttp.ClientTimeout(total=self._conn_options.timeout),
            ) as ws:
                # Send configuration
                await ws.send_json(
                    {
                        "type": "config",
                        "top_p": self._opts.top_p,
                        "repetition_penalty": self._opts.repetition_penalty,
                    }
                )

                # Task to send text chunks from input channel
                async def send_text() -> None:
                    nonlocal text_buffer, segment_id

                    async for data in self._input_ch:
                        if isinstance(data, self._FlushSentinel):
                            # Flush: send accumulated text as final and start new segment
                            if text_buffer:
                                await ws.send_json(
                                    {
                                        "type": "text",
                                        "content": text_buffer,
                                        "is_final": True,
                                    }
                                )
                                text_buffer = ""

                            # Start a new segment for next text
                            output_emitter.start_segment(segment_id=segment_id)
                            segment_id = utils.shortuuid()
                        else:
                            # Accumulate text
                            text_buffer += data
                            self._mark_started()

                            # Send text chunk (not final)
                            await ws.send_json(
                                {
                                    "type": "text",
                                    "content": data,
                                    "is_final": False,
                                }
                            )

                    # End of input - send final text if any remains
                    if text_buffer:
                        await ws.send_json(
                            {
                                "type": "text",
                                "content": text_buffer,
                                "is_final": True,
                            }
                        )
                    else:
                        # Send empty final to signal end
                        await ws.send_json(
                            {
                                "type": "text",
                                "content": "",
                                "is_final": True,
                            }
                        )

                # Task to receive audio from WebSocket
                async def receive_audio() -> None:
                    nonlocal segment_id

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            # Raw PCM16 audio
                            output_emitter.push(msg.data)
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                msg_type = data.get("type")

                                if msg_type == "done":
                                    output_emitter.end_input()
                                    break
                                elif msg_type == "error":
                                    raise APIError(data.get("message", "Unknown error"))
                                elif msg_type == "status":
                                    logger.debug(f"Luna TTS status: {data.get('message')}")
                            except json.JSONDecodeError:
                                continue
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            logger.warning(f"WebSocket closed: {msg.type}")
                            break

                # Start the first segment
                output_emitter.start_segment(segment_id=segment_id)

                # Run both tasks concurrently
                send_task = asyncio.create_task(send_text(), name="luna_send_text")
                receive_task = asyncio.create_task(receive_audio(), name="luna_receive_audio")

                try:
                    await asyncio.gather(send_task, receive_task)
                finally:
                    await utils.aio.gracefully_cancel(send_task, receive_task)

        except asyncio.TimeoutError:
            raise APITimeoutError() from None
        except aiohttp.ClientError as e:
            raise APIConnectionError(str(e)) from e
