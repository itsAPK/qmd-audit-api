from fastapi import APIRouter, Depends, status
from app.auth.services import AuthService
from app.core.schemas import Response, ResponseStatus
from app.auth.models import (
    ChangePasswordRequest,
    Login,
    LoginResponse,
    PasswordUpdateRequest,
)
from app.auth.dependencies import get_auth_service
from app.core.security import authenticate
from app.users.models import User, UserResponse


router = APIRouter()


@router.post(
    "/login", status_code=status.HTTP_200_OK, response_model=Response[LoginResponse]
)
async def login(data: Login, auth_service: AuthService = Depends(get_auth_service)):
    return Response(
        message="Login successful",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=await auth_service.login(data),
    )


@router.post(
    "/change-password", status_code=status.HTTP_200_OK, response_model=Response[bool]
)
async def change_password(
    data: ChangePasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user: User = Depends(authenticate),
):
    await auth_service.change_password(data, data.user_id)
    return Response(
        message="Password reset successful",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )
    
@router.post(
    "/reset-password", status_code=status.HTTP_200_OK, response_model=Response[bool]
)
async def password_reset(
    data: PasswordUpdateRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.password_reset(data)
    return Response(
        message="Password reset successful",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )
