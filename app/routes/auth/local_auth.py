import secrets
from datetime import datetime, timedelta
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from services.utils import get_logger
from schema import SignupForm, LoginForm
from database import User, get_db, RefreshToken
from services.auth import create_access_token, verify_password, hash_password

router = APIRouter()

logger = get_logger(__file__)


@router.post("/api/auth/signup")
async def signup(signup_form: SignupForm, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(User).where(User.email == signup_form.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")

        hashed_password = await run_in_threadpool(hash_password, signup_form.password)
        new_user = User(email=signup_form.email, password=hashed_password, name=signup_form.name)
        db.add(new_user)
        await db.commit()

        return {"status_code": 200, "data": "User Created Successfully!"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")


@router.post("/api/auth/login")
async def login(login_form: LoginForm, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(User).where(User.email == login_form.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        valid_pwd = await run_in_threadpool(
            verify_password, login_form.password, user.password
        )
        if not valid_pwd:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=timedelta(minutes=30)
        )
        refresh_token = secrets.token_urlsafe(64)

        cookie_max_age = 30 * 24 * 60 * 60
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,  # Prevents JavaScript access (XSS protection)
            secure=False,  # Ensures cookie is only sent over HTTPS (Set to False for localhost testing)
            samesite="lax",  # CSRF protection.
            max_age=cookie_max_age,
            path="/auth",  # Optional but recommended: Only send this cookie to /auth endpoints
        )

        return {
            "status_code": 200,
            "access_token": access_token,
            "token_type": "bearer",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")


@router.post("/auth/logout")
async def logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        stmt = select(RefreshToken).where(
            RefreshToken.token == refresh_token, RefreshToken.revoked == False
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if not db_token or db_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )

        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token == refresh_token)
            .values(revoked=True)
        )
        await db.execute(stmt)
        await db.commit()

        response.delete_cookie("refresh_token")
        return {"status_code": 200, "data": "User logged out Successfully."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")


@router.post("/auth/refresh")
async def refresh_access_token(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # Read the refresh token from the HttpOnly cookie
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        # Check the database
        stmt = select(RefreshToken).where(
            RefreshToken.token == refresh_token, RefreshToken.revoked == False
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if not db_token or db_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )

        # Issue a new Access Token
        new_access_token = create_access_token(
            data={"sub": db_token.user_email}, expires_delta=timedelta(minutes=30)
        )

        return {
            "status_code": 200,
            "access_token": new_access_token,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")
