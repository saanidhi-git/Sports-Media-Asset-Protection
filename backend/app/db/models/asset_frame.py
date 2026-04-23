from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class AssetFrame(Base):
    __tablename__ = "asset_frames"

    id = Column(Integer, primary_key=True, index=True)
    frame_number = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    phash_value = Column(String, nullable=True) # For future pHash implementation
    pdq_hash = Column(String(64), nullable=True) # Meta PDQ hash
    
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    asset = relationship("Asset", back_populates="frames")
