"""
Start System: Text Bridge

Connects the voice pipeline to the text processing pipeline.
Takes transcribed text from STT → sends through decision engine → returns response text.
This is the handoff point between System 6 (Start) and the rest of Quarky.
"""

from core.decision.output_gate import process, FinalOutput
from core.session.session import get_session


def handle_voice_input(text: str) -> str:
    """
    Process transcribed voice input through Quarky's brain.

    Takes raw text from STT, sends it through the full decision pipeline,
    records the session turn, and returns the response text for TTS.
    """
    if not text or not text.strip():
        return "I didn't catch that. Could you say it again?"

    text = text.strip()

    try:
        output: FinalOutput = process(text)
    except Exception:
        return "Something went wrong processing that. Try again?"

    # Record the turn in session
    session = get_session()
    action_str = ""
    if output.action_result and output.action_result.success:
        action_str = output.action_result.message or "Action completed"

    session.add_turn(
        user_text=text,
        response=output.response,
        source=output.source,
        confidence=output.confidence,
        action_performed=action_str,
    )

    return output.response


def handle_voice_command(text: str) -> dict:
    """
    Process voice input and return structured result (for state manager).
    Returns dict with response text, action info, and metadata.
    """
    if not text or not text.strip():
        return {
            "response": "I didn't catch that. Could you say it again?",
            "action": None,
            "success": True,
        }

    text = text.strip()

    try:
        output: FinalOutput = process(text)
    except Exception:
        return {
            "response": "Something went wrong. Try again?",
            "action": None,
            "success": False,
        }

    session = get_session()
    action_str = ""
    if output.action_result and output.action_result.success:
        action_str = output.action_result.message or "Action completed"

    session.add_turn(
        user_text=text,
        response=output.response,
        source=output.source,
        confidence=output.confidence,
        action_performed=action_str,
    )

    return {
        "response": output.response,
        "action": action_str or None,
        "success": True,
        "confidence": output.confidence,
        "source": output.source,
    }
