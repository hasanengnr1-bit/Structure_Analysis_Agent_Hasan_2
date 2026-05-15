import os
from jose import jwt
from sqlalchemy import select
from passlib.context import CryptContext
from datetime import timedelta, datetime
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

from database import User, get_db, RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession

# Configuration constants
SECRET_KEY = os.environ['ENCRYPTION_SECRET_KEY']
ALGORITHM = "HS256"

# Password hashing configuration
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    db: AsyncSession = Depends(get_db),    
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token expired\""}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

        
    user = await db.execute(select(User).filter(User.email == email))
    user = user.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user

async def store_refresh_token_in_db(db: AsyncSession, user_email: str, token_string: str) -> None:
    """Saves the token to the database with a 30-day expiration."""
    expires_at = datetime.utcnow() + timedelta(days=30) 
    
    db_token = RefreshToken(
        token=token_string,
        user_email=user_email,
        expires_at=expires_at,
        revoked=False
    )
    db.add(db_token)
    await db.commit()
