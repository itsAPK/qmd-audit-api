import logging
from typing import Optional
from uuid import UUID
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.core.security import get_password_hash
from app.settings.links import UserDepartment
from app.settings.models import Department
from app.users.models import (
    AssignUserDepartmentRequest,
    RemoveUserDepartmentRequest,
    RoleEnum,
    RoleRequest,
    RoleResponse,
    RoleUpdateRequest,
    UpdateUserRequest,
    User,
    UserCreateRequest,
    UserDepartmentResponse,
    UserListResponse,
    UserResponse,
    UserRole,
)
from fastapi import BackgroundTasks, HTTPException, status

from app.utils.dsl_filter import apply_sort, apply_filters
from app.utils.model_graph import ModelGraph


class UserService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build([User, UserDepartment, UserRole, Department])

    async def create_role(self, request: RoleRequest):
        role = UserRole(
            role=request.role,
            description=request.description,
            permissions=request.permissions,
        )
        self.session.add(role)
        await self.session.commit()
        return role

    async def get_all_roles(self):
        roles = await self.session.execute(select(UserRole))
        roles = roles.scalars().all()
        return roles

    async def get_role_by_id(self, role_id: UUID):
        role = await self.session.execute(
            select(UserRole)
            .where(UserRole.id == role_id)
            .options(
                selectinload(UserRole.departments).options(
                    selectinload(UserDepartment.user),
                    selectinload(UserDepartment.department),
                )
            )
        )
        role = role.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Role not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return role

    async def update_role(self, role_id: UUID, request: RoleUpdateRequest):
        role = await self.session.execute(
            select(UserRole).where(UserRole.id == role_id)
        )
        role = role.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Role not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        role.role = request.role
        role.description = request.description
        role.permissions = request.permissions
        await self.session.commit()
        return role

    async def delete_role(self, role_id: UUID):
        role = await self.session.execute(
            select(UserRole).where(UserRole.id == role_id)
        )
        role = role.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Role not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(role)
        await self.session.commit()
        return role

    async def create_user(self, data: UserCreateRequest):
        password = get_password_hash(data.password)
        user = User(
            employee_id=data.employee_id,
            password=password,
            email=data.email,
            qualification=data.qualification,
            designation=data.designation,
            role=data.role,
            name=data.name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: UUID, data: UpdateUserRequest):
        user = await self.session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        user.employee_id = data.employee_id or user.employee_id
        if data.password:
            user.password = get_password_hash(data.password)
        user.email = data.email or user.email
        user.qualification = data.qualification or user.qualification
        user.designation = data.designation or user.designation
        user.role = data.role or user.role
        user.name = data.name or user.name
        await self.session.commit()
        return user

    async def get_all_users(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        stmt = select(User).options(
            selectinload(User.departments).options(
                selectinload(UserDepartment.role),
                selectinload(UserDepartment.department),
            )
        )

        if filters:
            print(filters)
            # if "departments.role.role" in filters or "departments.department.name" in filters:
            #     stmt = stmt.join(
            #         UserDepartment, User.id == UserDepartment.user_id
            #     ).join(UserRole, UserDepartment.role_id == UserRole.id).join(Department, UserDepartment.department_id == Department.id)

            stmt = apply_filters(stmt, filters, User, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, User, self.graph)
        stmt = stmt.distinct()
        print(stmt)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        users = result.scalars().all()
        print(filters)

        response = UserListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                UserResponse(
                    id=user.id,
                    employee_id=user.employee_id,
                    password=user.password,
                    email=user.email,
                    qualification=user.qualification,
                    designation=user.designation,
                    name=user.name or "",
                    is_active=user.is_active,
                    role=user.role,
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
                )
                for user in users
            ],
        )

        return response

    async def assign_department_to_user(self, data: AssignUserDepartmentRequest):
        user_id = data.user_id
        department_id = data.department_id
        role_id = data.role_id
        user = await self.session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        department = await self.session.execute(
            select(Department).where(Department.id == department_id)
        )
        department = department.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Department not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        role = await self.session.execute(
            select(UserRole).where(UserRole.id == role_id)
        )
        role = role.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Role not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        user_department = UserDepartment(
            user_id=user_id,
            department_id=department_id,
            role_id=role_id,
        )
        self.session.add(user_department)
        await self.session.commit()
        return user_department

    async def remove_user_department(self, data: RemoveUserDepartmentRequest):
        user_department = await self.session.execute(
            select(UserDepartment).where(
                UserDepartment.department_id == data.department_id,
                UserDepartment.user_id == data.user_id,
            )
        )
        user_department = user_department.scalar_one_or_none()

        if not user_department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User department not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(user_department)
        await self.session.commit()
        return user_department

    async def export_users(
        self, filters: Optional[str] = None, sort: Optional[str] = "created_at.desc"
    ):
        stmt = select(User).options(
            selectinload(User.departments).options(
                selectinload(UserDepartment.role),
                selectinload(UserDepartment.department),
            )
        )
        if filters:
            stmt = apply_filters(stmt, filters, User, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, User, self.graph)
            
        stmt = stmt.distinct()

        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            UserResponse(
                id=user.id,
                employee_id=user.employee_id,
                password=user.password,
                email=user.email,
                qualification=user.qualification,
                designation=user.designation,
                is_active=user.is_active,
                role=user.role,
                name=user.name,
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
            )
            for user in users
        ]

    async def get_user_department_by_user_id(self, user_id: UUID):
        role = await self.session.execute(
            select(UserDepartment)
            .where(UserDepartment.user_id == user_id)
            .options(
                selectinload(UserDepartment.department),
                selectinload(UserDepartment.role),
            )
        )
        roles = role.scalars().all()
        return [
            UserDepartmentResponse(
                id=role.department_id,
                user_id=role.user_id,
                department_id=role.department_id,
                role_id=role.role_id,
                department=role.department,
                role=role.role,
            )
            for role in roles
        ]

    async def get_all_users_by_department(self, department_id: UUID):
        stmt = (
            select(UserDepartment)
            .where(UserDepartment.department_id == department_id)
            .options(
                selectinload(UserDepartment.user),
                selectinload(UserDepartment.role),
            )
        )

        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            UserDepartmentResponse(
                id=user_department.user_id,
                user_id=user_department.user_id,
                department_id=user_department.department_id,
                role_id=user_department.role_id,
                role=user_department.role,
                user=user_department.user,
            )
            for user_department in users
        ]

    async def upload_excel(self, file: bytes):
        try:
            print("Starting the Excel upload process.")
            df = pd.read_excel(file)
            print(f"Successfully read the Excel file with {len(df)} rows.")

            for _, row in df.iterrows():
                user_data = UserCreateRequest(
                    employee_id=str(row["Employee Id"]),
                    name=row["Name"],
                    email=row["E-mail"],
                    designation=row["Designation"],
                    qualification=row["Qualification"],
                    password=str(row["Employee Id"]),
                    role=RoleEnum.USER,
                )

                print(f"Processing user: {user_data.employee_id}")

                user = await self.session.execute(
                    select(User).where(User.employee_id == user_data.employee_id)
                )

                user = user.scalar_one_or_none()
                if user:
                    print(f"User {user_data.employee_id} found. Updating data.")

                    await self.update_user(user_id=user.id, data=user_data)

                else:
                    print(
                        f"Employee {user_data.employee_id} not found. Creating new record."
                    )
                    await self.create_user(user_data)

            return Response(
                message="Employee data imported from Excel file successfully",
                success=True,
                status=ResponseStatus.CREATED,
                data=None,
            )

        except Exception as e:
            print(f"Error in Excel upload process: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": str(e),
                    "success": False,
                    "status": ResponseStatus.FAILED,
                    "data": None,
                },
            )

    async def upload_excel_in_background(
        self, background_tasks: BackgroundTasks, file: bytes
    ):
        background_tasks.add_task(self.upload_excel, file)
        print("Excel file upload started in the background.")
        return Response(
            message="Excel file upload is in progress.",
            success=True,
            status=ResponseStatus.ACCEPTED,
            data=None,
        )

    async def get_all_users_by_role(self,
                                 
                                    filters : Optional[str] = None,
                                    sort : Optional[str] = None,
                                    ):
        stmt = (
            select(UserRole)
            .options(
                selectinload(UserRole.departments).options(
                    selectinload(UserDepartment.user),
                    selectinload(UserDepartment.department),
                )
            )
        )
        
        if filters:
            print(filters)
            stmt = apply_filters(stmt, filters, UserRole, self.graph)
            
        if sort:
            stmt = apply_sort(stmt, sort, UserRole, self.graph)
        stmt = stmt.distinct()
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            RoleResponse(
                id=role.id,
                role=role.role,
                description=role.description,
                permissions=role.permissions,
                users=[
                    UserDepartmentResponse(
                        id=department.department_id,
                        user_id=department.user_id,
                        department_id=department.department_id,
                        role_id=department.role_id,
                        department=department.department,
                        user=department.user,
                    )
                    for department in role.departments
                ],  
            )
            for role in users
        ]
