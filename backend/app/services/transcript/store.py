from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import AsyncSessionLocal
from app.models.meetings import Transcript
import logging
import datetime

logger = logging.getLogger(__name__)


class TranscriptStore:
    """Service for storing transcripts in the database."""
    
    async def store_final_transcript(self, 
                                   meeting_id: str,
                                   segment_no: int,
                                   text: str,
                                   start_ms: int,
                                   end_ms: int,
                                   speaker: Optional[str] = None,
                                   confidence: Optional[float] = None,
                                   raw_json: Optional[Dict[str, Any]] = None) -> bool:
        """Store a final transcript segment."""
        try:
            async with AsyncSessionLocal() as db:
                transcript = Transcript(
                    meeting_id=meeting_id,
                    segment_no=segment_no,
                    speaker=speaker,
                    text=text,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    is_final=True,
                    confidence=confidence,
                    raw_json=raw_json or {},
                    created_at=datetime.datetime.utcnow()
                )
                
                db.add(transcript)
                await db.commit()
                
                logger.info(f"Stored transcript segment {segment_no} for meeting {meeting_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store transcript: {e}")
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