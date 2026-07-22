import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import COOKIE_NAME, create_access_token, get_current_user_optional
from app.config import settings
from app.database import get_db
from app.github_client import exchange_code_for_token, fetch_github_user
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
async def github_login():
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri,
        "scope": "repo read:user",
        "allow_signup": "true",
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured on the server")

    access_token = await exchange_code_for_token(
        code,
        settings.github_client_id,
        settings.github_client_secret,
        settings.github_oauth_redirect_uri,
    )
    gh_user = await fetch_github_user(access_token)

    result = await db.execute(select(User).where(User.github_id == gh_user["id"]))
    user = result.scalar_one_or_none()

    if user:
        user.access_token = access_token
        user.username = gh_user["login"]
        user.avatar_url = gh_user.get("avatar_url")
    else:
        user = User(
            github_id=gh_user["id"],
            username=gh_user["login"],
            avatar_url=gh_user.get("avatar_url"),
            access_token=access_token,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    redirect = RedirectResponse(url=f"{settings.frontend_url}/auth/callback")
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return redirect


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=UserOut | None)
async def me(user: User | None = Depends(get_current_user_optional)):
    return user
