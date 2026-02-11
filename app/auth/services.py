from app.auth.models import ChangePasswordRequest, ForgotPassword, Login, LoginResponse, PasswordUpdateRequest
from app.core.security import create_access_token, get_password_hash, verify_password
from app.settings.links import UserDepartment
from app.users.models import User, UserDepartmentResponse, UserResponse
from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.core.schemas import ResponseStatus


class AuthService:
    def __init__(self, session):
        self.session = session

    async def login(self, data: Login):
        user = await self.session.execute(
            select(User)
            .where(User.employee_id == data.employee_id)
            .options(
                selectinload(User.departments).options(
                    selectinload(UserDepartment.role),
                    selectinload(UserDepartment.department),
                )
            )
        )
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Employee not found",
                    "success": False,
                    "status": ResponseStatus.DATA_NOT_FOUND.value,
                    "data": None,
                },
            )

        # if not verify_password(data.password, user.password):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail={
        #             "message": "Invalid password",
        #             "success": False,
        #             "status": ResponseStatus.FAILED.value,
        #             "data": None,
        #         },
        #     )

        access_token = create_access_token(
            subject=user.employee_id,
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                employee_id=user.employee_id,
                password=user.password,
                email=user.email,
                qualification=user.qualification,
                designation=user.designation,
                is_active=user.is_active,
                role=user.role,
                name = user.name or "",
                departments=[
                    UserDepartmentResponse(
                        id=department.department_id,
                        user_id=user.id,
                        department_id=department.department_id,
                        role_id=department.role_id,
                        department=department.department,
                        role=department.role,
                    )
                    for department in user.departments
                ],
            ))
        
    async def password_reset(self, data: PasswordUpdateRequest):
        user = await self.session.execute(
            select(User).where(User.employee_id == data.employee_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Employee not found",
                    "success": False,
                    "status": ResponseStatus.DATA_NOT_FOUND.value,
                    "data": None,
                },
            )
        if not verify_password(data.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid password",
                    "success": False,
                    "status": ResponseStatus.FAILED.value,
                    "data": None,
                },
            )
        user.password = get_password_hash(data.new_password)
        await self.session.commit()
        return user
    
    
    async def change_password(self, data: ChangePasswordRequest,user_id: str):
        user = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Employee not found",
                    "success": False,
                    "status": ResponseStatus.DATA_NOT_FOUND.value,
                    "data": None,
                },
            )
        if not verify_password(data.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid password",
                    "success": False,
                    "status": ResponseStatus.FAILED.value,
                    "data": None,
                },
            )
        user.password = get_password_hash(data.new_password)
        await self.session.commit()
        return user
    
