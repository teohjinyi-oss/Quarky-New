"""
System 6: Start — Voice Wake Word + STT/TTS

Pipeline: mic_listener → wake_detector → stt_engine → text_bridge → tts_engine
Orchestrated by state_manager.
"""

from AppStudio.Start.state_manager import start_voice, stop_voice, voice_status

__all__ = ["start_voice", "stop_voice", "voice_status"]
