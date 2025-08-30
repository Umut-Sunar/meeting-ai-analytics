from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import AsyncSessionLocal
from app.models.meetings import Transcript
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TranscriptStore:
    """Service for storing transcripts in the database."""
    
    async def store_final_transcript(self, 
                                   meeting_id: str,
                                   segment_no: int,
                                   transcript_text: str,
                                   start_ms: int,
                                   end_ms: int,
                                   deepgram_stream_id: str,
                                   speaker: Optional[str] = None,
                                   confidence: Optional[float] = None,
                                   raw_json: Optional[Dict[str, Any]] = None) -> bool:
        """Store a final transcript segment with idempotent key system."""
        try:
            async with AsyncSessionLocal() as db:
                # Generate idempotent key: {meeting_id}:{deepgram_stream_id}:{segment_index}
                idempotent_key = f"{meeting_id}:{deepgram_stream_id}:{segment_no}"
                
                # Check if already exists (duplicate prevention)
                existing = await db.execute(
                    text("SELECT id FROM transcripts WHERE idempotent_key = :key"),
                    {"key": idempotent_key}
                )
                if existing.fetchone():
                    logger.info(f"Transcript already exists with key: {idempotent_key}")
                    return True  # Already processed, return success
                
                # Create new transcript with idempotent key
                transcript = Transcript(
                    meeting_id=meeting_id,
                    segment_no=segment_no,
                    speaker=speaker,
                    text=transcript_text,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    is_final=True,
                    confidence=confidence,
                    raw_json=raw_json or {},
                    idempotent_key=idempotent_key
                    # created_at will be set automatically by model default
                )
                
                db.add(transcript)
                await db.commit()
                
                logger.info(f"✅ Stored transcript segment {segment_no} for meeting {meeting_id} with key: {idempotent_key}")
                return True
                
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to store transcript: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False
            
    async def get_meeting_transcripts(self, meeting_id: str) -> list[dict]:
        """Get all transcripts for a meeting."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT * FROM transcripts WHERE meeting_id = :meeting_id ORDER BY segment_no"),
                    {"meeting_id": meeting_id}
                )
                return [dict(r._mapping) for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get transcripts: {e}")
            return []


# Global instance
transcript_store = TranscriptStore()