"""
Real-time Deepgram client for live audio transcription.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Awaitable
from urllib.parse import urlencode

import websockets
from websockets.client import WebSocketClientProtocol

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DeepgramLiveClient:
    """Real-time Deepgram transcription client."""
    
    def __init__(
        self,
        meeting_id: str,
        language: str = "tr",
        sample_rate: int = 48000,
        channels: int = 1,
        model: str = "nova-2",
        on_transcript: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_error: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        self.meeting_id = meeting_id
        self.language = language
        self.sample_rate = sample_rate
        self.channels = channels
        self.model = model
        self.on_transcript = on_transcript
        self.on_error = on_error
        
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_finalizing = False
        self._listener_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.bytes_sent = 0
        self.frames_sent = 0
        self.transcripts_received = 0
        self.connected_at: Optional[datetime] = None
        
    async def connect(self) -> None:
        """Connect to Deepgram Live API."""
        print(f"🔧 DeepgramLiveClient.connect() CALLED for {self.meeting_id}")  # DEBUG
        print(f"🔧 is_connected: {self.is_connected}")  # DEBUG
        
        if self.is_connected:
            print(f"🔧 EARLY RETURN: already connected for {self.meeting_id}")  # DEBUG
            return
        
        if not settings.DEEPGRAM_API_KEY:
            print(f"🔧 NO API KEY for {self.meeting_id}")  # DEBUG
            raise ValueError("DEEPGRAM_API_KEY not configured")
        
        print(f"🔧 API KEY OK for {self.meeting_id}: ***{settings.DEEPGRAM_API_KEY[-4:]}")  # DEBUG
        
        # Build connection parameters
        params = {
            "model": self.model,
            "language": self.language,
            "punctuate": "true",
            "diarize": "true",
            "encoding": "linear16",
            "sample_rate": str(self.sample_rate),
            "channels": str(self.channels),
            "interim_results": "true",
            "utterance_end_ms": "1000",
            "vad_events": "true"
        }
        
        url = f"{settings.DEEPGRAM_ENDPOINT}?{urlencode(params)}"
        print(f"🔧 Deepgram URL for {self.meeting_id}: {url}")  # DEBUG
        
        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "User-Agent": "MeetingAI/1.0"
        }
        
        try:
            print(f"🔧 BEFORE websockets.connect() for {self.meeting_id}")  # DEBUG
            logger.info(f"🔗 Connecting to Deepgram: {self.model} ({self.language})")
            
            self.websocket = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            print(f"🔧 AFTER websockets.connect() SUCCESS for {self.meeting_id}")  # DEBUG
            self.is_connected = True
            self.connected_at = datetime.utcnow()
            
            # Start listener task
            self._listener_task = asyncio.create_task(self._listen_loop())
            
            logger.info(f"✅ Deepgram connected for meeting:{self.meeting_id}")
            print(f"🔧 DeepgramLiveClient.connect() COMPLETED for {self.meeting_id}")  # DEBUG
            
        except Exception as e:
            print(f"🔧 websockets.connect() EXCEPTION for {self.meeting_id}: {e}")  # DEBUG
            logger.error(f"❌ Failed to connect to Deepgram: {e}")
            await self._handle_error(f"Connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Deepgram."""
        if not self.is_connected:
            return
        
        self.is_connected = False
        
        try:
            # Cancel listener task
            if self._listener_task:
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass
            
            # Close WebSocket
            if self.websocket:
                await self.websocket.close()
            
            logger.info(f"✅ Deepgram disconnected for meeting:{self.meeting_id}")
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting from Deepgram: {e}")
    
    async def send_pcm(self, pcm_data: bytes) -> None:
        """
        Send PCM audio data to Deepgram.
        
        Args:
            pcm_data: Raw PCM audio data (16-bit LE)
        """
        if not self.is_connected or not self.websocket:
            raise RuntimeError("Not connected to Deepgram")
        
        if self.is_finalizing:
            logger.warning("⚠️ Cannot send audio while finalizing")
            return
        
        try:
            await self.websocket.send(pcm_data)
            
            # Update statistics
            self.bytes_sent += len(pcm_data)
            self.frames_sent += 1
            
            logger.debug(f"📤 Sent {len(pcm_data)} bytes to Deepgram")
            
        except Exception as e:
            logger.error(f"❌ Failed to send audio to Deepgram: {e}")
            await self._handle_error(f"Send failed: {e}")
            raise
    
    async def finalize(self) -> None:
        """Finalize the transcription session."""
        if not self.is_connected or not self.websocket:
            return
        
        if self.is_finalizing:
            return
        
        self.is_finalizing = True
        
        try:
            # Send CloseStream message  
            finalize_msg = json.dumps({"type": "CloseStream"})
            await self.websocket.send(finalize_msg)
            
            logger.info(f"🏁 CloseStream sent for meeting:{self.meeting_id}")
            
            # Wait a bit for final results
            await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.error(f"❌ Error finalizing Deepgram session: {e}")
        
        finally:
            await self.disconnect()
    
    async def _listen_loop(self) -> None:
        """Listen for messages from Deepgram."""
        try:
            while self.is_connected and self.websocket:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0
                    )
                    
                    if isinstance(message, str):
                        await self._handle_message(message)
                    else:
                        logger.warning(f"⚠️ Received non-text message from Deepgram")
                        
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Deepgram message timeout")
                    break
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info("📤 Deepgram connection closed")
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ Error in Deepgram listener: {e}")
            await self._handle_error(f"Listener error: {e}")
        
        finally:
            self.is_connected = False
    
    async def _handle_message(self, message_str: str) -> None:
        """Handle a message from Deepgram."""
        try:
            message = json.loads(message_str)
            message_type = message.get("type", "")
            
            if message_type == "Results":
                await self._handle_transcript_result(message)
                
            elif message_type == "Metadata":
                await self._handle_metadata(message)
                
            elif message_type == "SpeechStarted":
                logger.debug("🎤 Speech started")
                
            elif message_type == "UtteranceEnd":
                logger.debug("🛑 Utterance ended")
                
            elif message_type == "Error":
                error_msg = message.get("description", "Unknown error")
                logger.error(f"❌ Deepgram error: {error_msg}")
                await self._handle_error(f"Deepgram error: {error_msg}")
                
            else:
                logger.debug(f"📥 Deepgram message: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON from Deepgram: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling Deepgram message: {e}")
    
    async def _handle_transcript_result(self, result: Dict[str, Any]) -> None:
        """Handle transcript result from Deepgram."""
        try:
            channel = result.get("channel", {})
            alternatives = channel.get("alternatives", [])
            
            if not alternatives:
                return
            
            # Get best alternative
            best_alt = alternatives[0]
            transcript = best_alt.get("transcript", "").strip()
            confidence = best_alt.get("confidence", 0.0)
            
            if not transcript:
                return
            
            # Get timing info
            words = best_alt.get("words", [])
            start_ms = 0
            end_ms = 0
            
            if words:
                start_ms = int(words[0].get("start", 0) * 1000)
                end_ms = int(words[-1].get("end", 0) * 1000)
            
            # Determine if this is a final result
            is_final = channel.get("is_final", False)
            
            # Extract speaker info (if available)
            speaker = None
            if words and "speaker" in words[0]:
                speaker = f"Speaker {words[0]['speaker']}"
            
            # Create transcript data
            transcript_data = {
                "meeting_id": self.meeting_id,
                "text": transcript,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "is_final": is_final,
                "confidence": confidence,
                "speaker": speaker,
                "timestamp": datetime.utcnow().isoformat(),
                "raw_result": result  # Store full result for debugging
            }
            
            self.transcripts_received += 1
            
            logger.debug(
                f"📝 Transcript ({'final' if is_final else 'partial'}): "
                f"'{transcript}' ({confidence:.2f})"
            )
            
            # Call transcript handler
            if self.on_transcript:
                await self.on_transcript(transcript_data)
                
        except Exception as e:
            logger.error(f"❌ Error processing transcript result: {e}")
    
    async def _handle_metadata(self, metadata: Dict[str, Any]) -> None:
        """Handle metadata from Deepgram."""
        request_id = metadata.get("request_id", "")
        model_info = metadata.get("model_info", {})
        
        logger.info(
            f"📊 Deepgram session: {request_id}, "
            f"model: {model_info.get('name', 'unknown')}"
        )
    
    async def _handle_error(self, error_message: str) -> None:
        """Handle an error."""
        logger.error(f"❌ Deepgram error for meeting:{self.meeting_id}: {error_message}")
        
        if self.on_error:
            await self.on_error(error_message)
        
        # Disconnect on error
        self.is_connected = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        duration = 0
        if self.connected_at:
            duration = (datetime.utcnow() - self.connected_at).total_seconds()
        
        return {
            "meeting_id": self.meeting_id,
            "is_connected": self.is_connected,
            "is_finalizing": self.is_finalizing,
            "language": self.language,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "model": self.model,
            "duration_seconds": duration,
            "bytes_sent": self.bytes_sent,
            "frames_sent": self.frames_sent,
            "transcripts_received": self.transcripts_received,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None
        }
