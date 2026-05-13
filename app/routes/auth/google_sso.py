import os
import secrets
from sqlalchemy import select
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Request, Depends, Response, HTTPException

from database import get_db, User
from services.utils import get_logger
from services.auth import create_access_token

router = APIRouter()
oauth = OAuth()
logger = get_logger(__file__)

# Register Google OIDC
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID", "your_client_id"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_client_secret"),
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/api/login/google")
async def login_via_google(request: Request):
    try:
        # This generates the URL to Google's consent screen and redirects the user
        redirect_uri = request.url_for("auth_via_google_callback")
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")


@router.get("/auth/google/callback")
async def auth_via_google_callback(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    try:
        # Exchange the code for an access token from Google
        token = await oauth.google.authorize_access_token(request)
    
        # Because we are using OIDC, the user info is usually inside the token object
        user_info = token.get("userinfo")

        # Fallback just in case
        if not user_info:
            user_info = await oauth.google.parse_id_token(request, token)

        email = user_info.get("email")
        name = user_info.get("name")
        # google_id = user_info.get("sub")  # Google's unique user ID

        # Check the database for this user
        stmt = select(User).where(
            User.email == email
        )
        user = await db.execute(stmt)
        user = user.scalar_one_or_none()

        # If user doesn't exist, create a new user account on the fly.
        if not user:
            user = User(email=email, name=name)
            db.add(user)
            await db.commit()

        # Generate JWT token
        jwt_token = create_access_token(
            data={"sub": email}, expires_delta=timedelta(minutes=30)
        )
        refresh_token = secrets.token_urlsafe(64)

        cookie_max_age = 30 * 24 * 60 * 60 
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,  # Prevents JavaScript access (XSS protection)
            secure=False,    # Ensures cookie is only sent over HTTPS (Set to False for localhost testing)
            samesite="lax", # CSRF protection.
            max_age=cookie_max_age,
            path="/auth"    # Optional but recommended: Only send this cookie to /auth endpoints
        )

        return {"status_code": 200, "access_token": jwt_token, "token_type": "bearer"}

    except OAuthError as error:
        return {"error": error.error}

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Something Went Wrong!")
