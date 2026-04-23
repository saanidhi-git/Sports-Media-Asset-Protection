from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class ScrapedFrame(Base):
    __tablename__ = "scraped_frames"

    id = Column(Integer, primary_key=True, index=True)
    frame_number = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    phash_value = Column(String, nullable=True)
    pdq_hash = Column(String(64), nullable=True)
    
    scraped_video_id = Column(Integer, ForeignKey("scraped_videos.id", ondelete="CASCADE"), nullable=False)
    scraped_video = relationship("ScrapedVideo", back_populates="frames")
