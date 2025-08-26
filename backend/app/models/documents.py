"""
Document management and file storage models.
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base


class Document(Base):
    """User-uploaded documents with tenant isolation."""
    
    __tablename__ = "documents"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Uploader reference
    uploader_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Document metadata
    title = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)  # S3 object key
    mime_type = Column(String(100), nullable=False)  # MIME type
    size_bytes = Column(BigInteger, nullable=False)
    
    # Vector indexing for RAG
    indexed = Column(Boolean, default=False, nullable=False)
    vector_idx_id = Column(String(255), nullable=True)  # External vector store ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    uploader = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_documents_tenant_id', 'tenant_id'),
        Index('ix_documents_uploader_user_id', 'uploader_user_id'),
        Index('ix_documents_s3_key', 's3_key'),
        Index('ix_documents_indexed', 'indexed'),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', title='{self.title}', size={self.size_bytes})>"
