"""
SQLAlchemy models for Video Rewards App
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """User model - stores Telegram user data"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    # Stars balance
    stars = Column(Integer, default=0)

    # Referral system
    referral_code = Column(String(32), unique=True, index=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Subscription status
    is_subscribed = Column(Boolean, default=False)
    subscription_reward_claimed = Column(Boolean, default=False)

    # Discount
    discount_claimed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    referred_by = relationship("User", remote_side=[id], backref="referrals")
    video_views = relationship("VideoView", back_populates="user")

    def __repr__(self):
        return f"<User {self.telegram_id}: {self.first_name}>"


class Video(Base):
    """Video model - stores video information"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(String(2000), nullable=True)
    video_url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    duration_seconds = Column(Integer, default=0)

    # Reward settings
    reward_stars = Column(Integer, default=1)
    min_watch_percent = Column(Integer, default=80)  # Minimum % to watch for reward

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    views = relationship("VideoView", back_populates="video")

    def __repr__(self):
        return f"<Video {self.id}: {self.title}>"


class VideoView(Base):
    """Video view tracking - records user video watches"""
    __tablename__ = "video_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)

    # Watch progress
    watch_progress = Column(Integer, default=0)  # Percentage watched
    completed = Column(Boolean, default=False)
    reward_claimed = Column(Boolean, default=False)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="video_views")
    video = relationship("Video", back_populates="views")

    def __repr__(self):
        return f"<VideoView user={self.user_id} video={self.video_id}>"


class ReferralReward(Base):
    """Tracks referral rewards to prevent duplicates"""
    __tablename__ = "referral_rewards"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    referred_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stars_awarded = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
