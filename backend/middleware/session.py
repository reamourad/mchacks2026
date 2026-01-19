import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from config import get_settings

settings = get_settings()


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get or create session ID
        session_id = request.cookies.get(settings.session_cookie_name)

        if not session_id:
            session_id = str(uuid.uuid4())

        # Store session_id in request state for access in routes
        request.state.session_id = session_id

        response: Response = await call_next(request)

        # Set cookie if it was newly created
        if settings.session_cookie_name not in request.cookies:
            response.set_cookie(
                key=settings.session_cookie_name,
                value=session_id,
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax",
                max_age=60 * 60 * 24 * 30,  # 30 days
            )

        return response


def get_session_id(request: Request) -> str:
    return request.state.session_id
