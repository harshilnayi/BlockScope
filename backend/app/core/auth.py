"""
BlockScope API Key Authentication System
Provides secure API key management and authentication
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.database import Base, get_db
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.orm import Session

# ==================== Database Models ====================


class APIKey(Base):
    """
    API Key model for storing and managing API keys
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    # API Key details
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    key_prefix = Column(String(16), nullable=False, index=True)  # First 8 chars for identification
    name = Column(String(255), nullable=False)  # Human-readable name
    description = Column(String(1000), nullable=True)

    # User/Owner information
    user_id = Column(Integer, nullable=True, index=True)  # Link to user if applicable
    owner_email = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Rate limit tier
    tier = Column(String(50), default="free", nullable=False)  # free, pro, enterprise

    # Usage tracking
    total_requests = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    revoked_at = Column(DateTime, nullable=True)

    # Security
    allowed_ips = Column(String(1000), nullable=True)  # Comma-separated IPs
    allowed_domains = Column(String(1000), nullable=True)  # Comma-separated domains

    # Indexes for performance
    __table_args__ = (
        Index("idx_api_keys_active", "is_active", "is_revoked"),
        Index("idx_api_keys_tier", "tier"),
        Index("idx_api_keys_created", "created_at"),
    )

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... - {self.name}>"


# ==================== API Key Generation ====================


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a secure API key.

    Returns:
        tuple: (raw_key, key_hash, key_prefix)
            - raw_key: The actual API key to show user (only once!)
            - key_hash: SHA256 hash to store in database
            - key_prefix: First 8 characters for identification
    """
    # Generate random key
    random_part = secrets.token_urlsafe(settings.API_KEY_LENGTH)

    # Add prefix
    raw_key = f"{settings.API_KEY_PREFIX}{random_part}"

    # Generate hash for storage (never store raw key!)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Extract prefix for identification
    key_prefix = raw_key[:12]  # prefix + first few chars

    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """
    Hash an API key for storage or comparison.

    Args:
        raw_key: Raw API key string

    Returns:
        str: SHA256 hash of the key
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ==================== API Key CRUD Operations ====================


def create_api_key(
    db: Session,
    name: str,
    description: Optional[str] = None,
    user_id: Optional[int] = None,
    owner_email: Optional[str] = None,
    tier: str = "free",
    expires_in_days: Optional[int] = None,
    allowed_ips: Optional[list] = None,
    allowed_domains: Optional[list] = None,
) -> tuple[str, APIKey]:
    """
    Create a new API key.

    Args:
        db: Database session
        name: Human-readable name for the key
        description: Optional description
        user_id: User ID if linked to a user
        owner_email: Owner's email
        tier: Rate limit tier (free, pro, enterprise)
        expires_in_days: Optional expiration in days
        allowed_ips: List of allowed IP addresses
        allowed_domains: List of allowed domains

    Returns:
        tuple: (raw_key, api_key_model)
            - raw_key: The API key to show user (ONLY ONCE!)
            - api_key_model: Database model
    """
    # Generate key
    raw_key, key_hash, key_prefix = generate_api_key()

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    # Create model
    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        description=description,
        user_id=user_id,
        owner_email=owner_email,
        tier=tier,
        expires_at=expires_at,
        allowed_ips=",".join(allowed_ips) if allowed_ips else None,
        allowed_domains=",".join(allowed_domains) if allowed_domains else None,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return raw_key, api_key


def validate_api_key(
    db: Session, raw_key: str, client_ip: Optional[str] = None
) -> Optional[APIKey]:
    """
    Validate an API key and return the model if valid.

    Args:
        db: Database session
        raw_key: Raw API key from request
        client_ip: Client IP address for IP validation

    Returns:
        APIKey: API key model if valid, None otherwise
    """
    # Hash the provided key
    key_hash = hash_api_key(raw_key)

    # Query database
    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.key_hash == key_hash, APIKey.is_active.is_(True), APIKey.is_revoked.is_(False)
        )
        .first()
    )

    if not api_key:
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None

    # Check IP restriction
    if api_key.allowed_ips and client_ip:
        allowed = [ip.strip() for ip in api_key.allowed_ips.split(",")]
        if client_ip not in allowed:
            return None

    # Update usage
    api_key.total_requests += 1
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    return api_key


def revoke_api_key(db: Session, key_id: int) -> bool:
    """
    Revoke an API key.

    Args:
        db: Database session
        key_id: API key ID

    Returns:
        bool: True if revoked successfully
    """
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        return False

    api_key.is_revoked = True
    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()
    db.commit()

    return True


def list_api_keys(
    db: Session, user_id: Optional[int] = None, include_revoked: bool = False
) -> list[APIKey]:
    """
    List API keys.

    Args:
        db: Database session
        user_id: Filter by user ID
        include_revoked: Include revoked keys

    Returns:
        list: List of API key models
    """
    query = db.query(APIKey)

    if user_id:
        query = query.filter(APIKey.user_id == user_id)

    if not include_revoked:
        query = query.filter(APIKey.is_revoked.is_(False))

    return query.order_by(APIKey.created_at.desc()).all()


# ==================== FastAPI Authentication ====================

# API Key header dependency
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)


async def get_api_key(
    api_key: str = Security(api_key_header), db: Session = Depends(get_db)
) -> APIKey:
    """
    FastAPI dependency to validate API key from header.

    Args:
        api_key: API key from header
        db: Database session

    Returns:
        APIKey: Validated API key model

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Please provide a valid API key in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate key
    validated_key = validate_api_key(db, api_key)

    if not validated_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return validated_key


async def get_optional_api_key(
    api_key: Optional[str] = Security(api_key_header), db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    Optional API key authentication.
    Returns None if no key provided, validates if present.

    Args:
        api_key: Optional API key from header
        db: Database session

    Returns:
        Optional[APIKey]: Validated API key or None
    """
    if not api_key:
        return None

    return validate_api_key(db, api_key)


# ==================== Rate Limit Helper ====================


def get_rate_limits(api_key: Optional[APIKey] = None) -> dict:
    """
    Get rate limits based on API key tier or default.

    Args:
        api_key: API key model (if authenticated)

    Returns:
        dict: Rate limits {per_minute, per_hour, per_day}
    """
    if not api_key:
        # Unauthenticated limits
        return {
            "per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.RATE_LIMIT_PER_HOUR,
            "per_day": settings.RATE_LIMIT_PER_DAY,
        }

    # Tier-based limits
    tier_limits = {
        "free": {
            "per_minute": settings.API_KEY_RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.API_KEY_RATE_LIMIT_PER_HOUR,
            "per_day": settings.API_KEY_RATE_LIMIT_PER_DAY,
        },
        "pro": {"per_minute": 100, "per_hour": 1000, "per_day": 10000},
        "enterprise": {"per_minute": 500, "per_hour": 5000, "per_day": 50000},
    }

    return tier_limits.get(api_key.tier, tier_limits["free"])


# ==================== Usage Example ====================
"""
# In your FastAPI endpoint:

from fastapi import APIRouter, Depends
from app.core.auth import get_api_key, APIKey

router = APIRouter()

@router.get("/protected-endpoint")
async def protected_endpoint(
    api_key: APIKey = Depends(get_api_key)
):
    # This endpoint requires valid API key
    return {
        "message": "Success",
        "api_key_name": api_key.name,
        "tier": api_key.tier
    }

@router.get("/optional-auth-endpoint")
async def optional_auth_endpoint(
    api_key: Optional[APIKey] = Depends(get_optional_api_key)
):
    # This endpoint works with or without API key
    if api_key:
        return {"message": "Authenticated", "tier": api_key.tier}
    else:
        return {"message": "Anonymous"}
"""
