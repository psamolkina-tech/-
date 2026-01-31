"""
FastAPI backend for Telegram Video Rewards Mini App
"""
import os
import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from dotenv import load_dotenv

from database import init_db, get_session, async_session
from models import User, Video, VideoView, ReferralReward

load_dotenv()

app = FastAPI(title="Video Rewards Mini App")

# CORS for Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bot token for validation
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # e.g., @yourchannel or -1001234567890

# Constants
STARS_FOR_DISCOUNT = 3
DISCOUNT_AMOUNT = 60000  # rubles


# Pydantic models
class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    referral_code: Optional[str] = None


class VideoProgress(BaseModel):
    video_id: int
    progress: int  # 0-100


class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    stars: int
    referral_code: str
    is_subscribed: bool
    subscription_reward_claimed: bool
    discount_claimed: bool
    discount_available: bool

    class Config:
        from_attributes = True


class VideoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    video_url: str
    thumbnail_url: Optional[str]
    duration_seconds: int
    reward_stars: int
    is_watched: bool = False
    reward_claimed: bool = False
    watch_progress: int = 0

    class Config:
        from_attributes = True


def generate_referral_code() -> str:
    """Generate unique referral code"""
    return secrets.token_urlsafe(8)


def validate_telegram_data(init_data: str) -> Optional[dict]:
    """Validate Telegram Mini App init data"""
    if not BOT_TOKEN:
        # Skip validation in development
        return None

    try:
        parsed_data = dict(x.split('=', 1) for x in init_data.split('&'))
        hash_value = parsed_data.pop('hash', None)

        if not hash_value:
            return None

        # Sort and create data check string
        data_check_string = '\n'.join(
            f"{k}={unquote(v)}" for k, v in sorted(parsed_data.items())
        )

        # Calculate secret key
        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if calculated_hash == hash_value:
            user_data = parsed_data.get('user')
            if user_data:
                return json.loads(unquote(user_data))
        return None
    except Exception:
        return None


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    referral_code: str = None
) -> User:
    """Get existing user or create new one"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referral_code=generate_referral_code()
        )

        # Handle referral
        if referral_code:
            referrer_result = await session.execute(
                select(User).where(User.referral_code == referral_code)
            )
            referrer = referrer_result.scalar_one_or_none()
            if referrer and referrer.telegram_id != telegram_id:
                user.referred_by_id = referrer.id

        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Award referral bonus
        if user.referred_by_id:
            referrer_result = await session.execute(
                select(User).where(User.id == user.referred_by_id)
            )
            referrer = referrer_result.scalar_one_or_none()
            if referrer:
                # Check if reward already given
                existing_reward = await session.execute(
                    select(ReferralReward).where(
                        and_(
                            ReferralReward.referrer_id == referrer.id,
                            ReferralReward.referred_id == user.id
                        )
                    )
                )
                if not existing_reward.scalar_one_or_none():
                    referrer.stars += 1
                    reward = ReferralReward(
                        referrer_id=referrer.id,
                        referred_id=user.id,
                        stars_awarded=1
                    )
                    session.add(reward)
                    await session.commit()

    return user


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()

    # Add sample videos if none exist
    async with async_session() as session:
        result = await session.execute(select(Video))
        if not result.scalars().first():
            sample_videos = [
                Video(
                    title="Добро пожаловать!",
                    description="Узнайте как работает наше приложение",
                    video_url="https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                    thumbnail_url="https://via.placeholder.com/320x180/667eea/ffffff?text=Video+1",
                    duration_seconds=60,
                    reward_stars=1
                ),
                Video(
                    title="Специальное предложение",
                    description="Посмотрите видео о наших акциях",
                    video_url="https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_2mb.mp4",
                    thumbnail_url="https://via.placeholder.com/320x180/764ba2/ffffff?text=Video+2",
                    duration_seconds=120,
                    reward_stars=1
                ),
                Video(
                    title="Как получить скидку",
                    description="Инструкция по получению скидки 60000 рублей",
                    video_url="https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_5mb.mp4",
                    thumbnail_url="https://via.placeholder.com/320x180/f093fb/ffffff?text=Video+3",
                    duration_seconds=180,
                    reward_stars=1
                ),
            ]
            session.add_all(sample_videos)
            await session.commit()


@app.post("/api/auth", response_model=UserResponse)
async def authenticate_user(
    user_data: UserCreate,
    init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_session)
):
    """Authenticate user and return profile"""
    # Validate Telegram data in production
    if BOT_TOKEN and init_data:
        validated = validate_telegram_data(init_data)
        if validated:
            user_data.telegram_id = validated.get('id', user_data.telegram_id)
            user_data.username = validated.get('username', user_data.username)
            user_data.first_name = validated.get('first_name', user_data.first_name)

    user = await get_or_create_user(
        session,
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        referral_code=user_data.referral_code
    )

    return UserResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        stars=user.stars,
        referral_code=user.referral_code,
        is_subscribed=user.is_subscribed,
        subscription_reward_claimed=user.subscription_reward_claimed,
        discount_claimed=user.discount_claimed,
        discount_available=user.stars >= STARS_FOR_DISCOUNT and not user.discount_claimed
    )


@app.get("/api/user/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get user profile"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        stars=user.stars,
        referral_code=user.referral_code,
        is_subscribed=user.is_subscribed,
        subscription_reward_claimed=user.subscription_reward_claimed,
        discount_claimed=user.discount_claimed,
        discount_available=user.stars >= STARS_FOR_DISCOUNT and not user.discount_claimed
    )


@app.get("/api/videos")
async def get_videos(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Get all videos with user watch status"""
    # Get user
    user_result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()

    # Get all active videos
    videos_result = await session.execute(
        select(Video).where(Video.is_active == True).order_by(Video.id)
    )
    videos = videos_result.scalars().all()

    response = []
    for video in videos:
        video_data = {
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "video_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
            "duration_seconds": video.duration_seconds,
            "reward_stars": video.reward_stars,
            "is_watched": False,
            "reward_claimed": False,
            "watch_progress": 0
        }

        if user:
            # Check if user has watched this video
            view_result = await session.execute(
                select(VideoView).where(
                    and_(
                        VideoView.user_id == user.id,
                        VideoView.video_id == video.id
                    )
                )
            )
            view = view_result.scalar_one_or_none()
            if view:
                video_data["is_watched"] = view.completed
                video_data["reward_claimed"] = view.reward_claimed
                video_data["watch_progress"] = view.watch_progress

        response.append(video_data)

    return response


@app.post("/api/video/progress")
async def update_video_progress(
    data: VideoProgress,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Update video watch progress and award stars if completed"""
    # Get user
    user_result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get video
    video_result = await session.execute(
        select(Video).where(Video.id == data.video_id)
    )
    video = video_result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get or create video view
    view_result = await session.execute(
        select(VideoView).where(
            and_(
                VideoView.user_id == user.id,
                VideoView.video_id == video.id
            )
        )
    )
    view = view_result.scalar_one_or_none()

    stars_earned = 0

    if not view:
        view = VideoView(
            user_id=user.id,
            video_id=video.id,
            watch_progress=data.progress
        )
        session.add(view)
    else:
        view.watch_progress = max(view.watch_progress, data.progress)

    # Check if video is completed and reward should be given
    if data.progress >= video.min_watch_percent and not view.completed:
        view.completed = True
        view.completed_at = datetime.utcnow()

    # Award stars if not already claimed
    if view.completed and not view.reward_claimed:
        view.reward_claimed = True
        user.stars += video.reward_stars
        stars_earned = video.reward_stars

    await session.commit()

    return {
        "success": True,
        "progress": view.watch_progress,
        "completed": view.completed,
        "reward_claimed": view.reward_claimed,
        "stars_earned": stars_earned,
        "total_stars": user.stars,
        "discount_available": user.stars >= STARS_FOR_DISCOUNT and not user.discount_claimed
    }


@app.post("/api/subscribe/check")
async def check_subscription(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Check channel subscription and award star"""
    # Get user
    user_result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # In production, you would check subscription via Telegram Bot API
    # For now, we'll simulate with a manual confirmation
    # The bot should call this endpoint after verifying subscription

    stars_earned = 0

    if not user.subscription_reward_claimed:
        user.is_subscribed = True
        user.subscription_reward_claimed = True
        user.stars += 1
        stars_earned = 1
        await session.commit()

    return {
        "success": True,
        "is_subscribed": user.is_subscribed,
        "stars_earned": stars_earned,
        "total_stars": user.stars,
        "discount_available": user.stars >= STARS_FOR_DISCOUNT and not user.discount_claimed
    }


@app.post("/api/discount/claim")
async def claim_discount(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Claim discount when user has enough stars"""
    # Get user
    user_result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.stars < STARS_FOR_DISCOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stars. Need {STARS_FOR_DISCOUNT}, have {user.stars}"
        )

    if user.discount_claimed:
        raise HTTPException(status_code=400, detail="Discount already claimed")

    user.discount_claimed = True
    await session.commit()

    # Generate discount code
    discount_code = f"DISCOUNT-{user.telegram_id}-{secrets.token_hex(4).upper()}"

    return {
        "success": True,
        "discount_code": discount_code,
        "discount_amount": DISCOUNT_AMOUNT,
        "message": f"Поздравляем! Ваша скидка {DISCOUNT_AMOUNT} рублей активирована!"
    }


@app.get("/api/referral/stats")
async def get_referral_stats(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Get user's referral statistics"""
    # Get user
    user_result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count referrals
    referrals_result = await session.execute(
        select(User).where(User.referred_by_id == user.id)
    )
    referrals = referrals_result.scalars().all()

    return {
        "referral_code": user.referral_code,
        "referral_count": len(referrals),
        "referral_link": f"https://t.me/YOUR_BOT?startapp={user.referral_code}"
    }


# Serve frontend
@app.get("/")
async def serve_index():
    """Serve main page"""
    return FileResponse("../frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
