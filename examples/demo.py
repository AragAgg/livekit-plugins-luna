#!/usr/bin/env python3
"""
=============================================================================
Luna Hindi TTS Demo Script
=============================================================================

This script demonstrates how to use the Luna TTS plugin to convert Hindi text
to speech. It's designed to be simple and easy to understand.

WHAT THIS SCRIPT DOES:
    1. Takes Hindi text as a command line argument
    2. Sends it to the Luna TTS API
    3. Receives audio back
    4. Saves it as a .wav file you can play

HOW TO RUN:
    See examples/SETUP.md for complete setup instructions.
    
    Quick start:
        python demo.py "नमस्ते, आप कैसे हैं?"

=============================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================

import asyncio      # For running async code
import sys          # For reading command line arguments
import wave         # For saving audio as .wav files
from datetime import datetime
from pathlib import Path

import aiohttp      # For making HTTP requests


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def convert_text_to_speech(text: str, session: aiohttp.ClientSession) -> str:
    """
    Convert Hindi text to speech and save as a .wav file.
    
    Args:
        text: The Hindi text you want to convert to speech
        session: HTTP session for making API requests
        
    Returns:
        Path to the saved .wav file
    """
    # Import the Luna TTS plugin
    from livekit.plugins.luna import TTS
    from livekit import rtc
    
    # Create a TTS instance
    # We pass the session so it can make HTTP requests
    tts = TTS(http_session=session)
    
    print(f"\n[TTS] Converting to speech:")
    print(f"      \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
    print("      Processing", end="", flush=True)
    
    # Call the API to synthesize speech
    # This returns a stream of audio chunks
    stream = tts.synthesize(text)
    
    # Collect all audio chunks
    audio_frames = []
    async for audio_chunk in stream:
        audio_frames.append(audio_chunk.frame)
        print(".", end="", flush=True)  # Show progress
    
    print(" Done!")
    
    # Check if we received any audio
    if not audio_frames:
        print("      [ERROR] No audio received from API")
        return None
    
    # Combine all audio chunks into one
    combined_audio = rtc.combine_audio_frames(audio_frames)
    
    # Generate a filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path.cwd() / f"output_{timestamp}.wav"
    
    # Save the audio as a .wav file
    # Luna TTS outputs: 32kHz sample rate, 16-bit, mono
    with wave.open(str(output_file), "wb") as wav_file:
        wav_file.setnchannels(1)        # Mono audio
        wav_file.setsampwidth(2)        # 16-bit = 2 bytes
        wav_file.setframerate(32000)    # 32kHz sample rate
        wav_file.writeframes(combined_audio.data)
    
    # Print results
    print(f"      [OK] Duration: {combined_audio.duration:.2f} seconds")
    print(f"      [OK] Saved to: {output_file}")
    
    # Clean up
    await tts.aclose()
    
    return str(output_file)


async def main():
    """
    Main entry point for the script.
    """
    # Check if text was provided as command line argument
    if len(sys.argv) < 2:
        print("\nUsage: python demo.py \"<Hindi text>\"")
        print("\nExample:")
        print("  python demo.py \"नमस्ते, आप कैसे हैं?\"")
        print("\nSee SETUP.md for complete instructions.")
        sys.exit(1)
    
    # Get the text from command line arguments
    text = " ".join(sys.argv[1:])
    
    # Create an HTTP session and convert the text
    async with aiohttp.ClientSession() as session:
        await convert_text_to_speech(text, session)


# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
