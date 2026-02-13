from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, status
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.core.security import authenticate
from app.settings.links import UserDepartment
from app.users.models import (
    AssignUserDepartmentRequest,
    RemoveUserDepartmentRequest,
    RoleRequest,
    RoleResponse,
    RoleUpdateRequest,
    RolesResponseList,
    UpdateUserRequest,
    User,
    UserCreateRequest,
    UserDepartmentResponse,
    UserListResponse,
    UserResponse,
    UserRole,
)
from app.users.dependencies import get_user_service
from app.users.services import UserService


router = APIRouter()


@router.post(
    "/roles", status_code=status.HTTP_201_CREATED, response_model=Response[UserRole]
)
async def create_role(
    request: RoleRequest, user_service: UserService = Depends(get_user_service)
):

    role = await user_service.create_role(request)

    return Response(
        message="Role created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=role,
    )


@router.get(
    "/roles", status_code=status.HTTP_200_OK, response_model=Response[RolesResponseList]
)
async def get_all_roles(user_service: UserService = Depends(get_user_service)):
    roles = await user_service.get_all_roles()
    return Response(
        message="Roles fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=RolesResponseList(
            roles=[
                RoleResponse(
                    id=role.id,
                    role=role.role,
                    description=role.description,
                    permissions=role.permissions,
                )
                for role in roles
            ]
        ),
    )
    

@router.get(
    "/roles/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[RoleResponse],
)
async def get_role_by_id(
    role_id: UUID, user_service: UserService = Depends(get_user_service)
):
    role = await user_service.get_role_by_id(role_id)
    return Response(
        message="Role fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=RoleResponse(
            id=role_id,
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
        ),
    )


@router.patch(
    "/roles/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[UserRole],
)
async def update_role(
    role_id: UUID,
    request: RoleUpdateRequest,
    user_service: UserService = Depends(get_user_service),
):
    role = await user_service.update_role(role_id, request)
    return Response(
        message="Role updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=role,
    )


@router.delete(
    "/roles/{role_id}", status_code=status.HTTP_200_OK, response_model=Response[bool]
)
async def delete_role(
    role_id: UUID, user_service: UserService = Depends(get_user_service)
):
    role = await user_service.delete_role(role_id)
    return Response(
        message="Role deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post(
    "/users", status_code=status.HTTP_201_CREATED, response_model=Response[User]
)
async def create_user(
    request: UserCreateRequest, user_service: UserService = Depends(get_user_service)
):

    user = await user_service.create_user(request)

    return Response(
        message="User created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user,
    )


@router.post(
    "/assign-department",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[UserDepartment],
)
async def assign_department_to_user(
    request: AssignUserDepartmentRequest,
    user_service: UserService = Depends(get_user_service),
):

    user_department = await user_service.assign_department_to_user(request)

    return Response(
        message="User department assigned successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user_department,
    )


@router.get(
    "/remove-department",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[UserDepartment],
)
async def remove_user_department(
    user_id: UUID,
    department_id: UUID,
    user_service: UserService = Depends(get_user_service),
):

    user_department = await user_service.remove_user_department(
        data=RemoveUserDepartmentRequest(
            user_id=user_id, department_id=department_id
        )
    )

    return Response(
        message="User department removed successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user_department,
    )


@router.get(
    "", status_code=status.HTTP_200_OK, response_model=Response[UserListResponse]
)
async def get_all_users(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    user_service: UserService = Depends(get_user_service),
):
    users = await user_service.get_all_users(filters, sort, page, page_size)
    return Response(
        message="Users fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=users,
    )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[UserResponse]],
)
async def export_users(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    user_service: UserService = Depends(get_user_service),
):
    users = await user_service.export_users(filters, sort)
    return Response(
        message="Users fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=users,
    )
    
@router.get(
    "/department/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[UserDepartmentResponse]],
)
async def get_user_department_by_user_id(
    user_id : UUID,
    user_service: UserService = Depends(get_user_service),
    user : User = Depends(authenticate),
):

    user_department = await user_service.get_user_department_by_user_id(user_id)

    return Response(
        message="User department fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user_department,
    )
    
@router.get(
    "/department/{department_id}/users",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[UserDepartmentResponse]],
)
async def get_all_users_by_department(
    department_id : UUID,
    user_service: UserService = Depends(get_user_service),
    user : User = Depends(authenticate),
):

    user_department = await user_service.get_all_users_by_department(department_id)

    return Response(
        message="User department fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user_department,
    )


@router.post("/upload/bulk", status_code=status.HTTP_200_OK)
async def upload(file: UploadFile,background_tasks: BackgroundTasks,_service: UserService = Depends(get_user_service)):
        print(file)
        result = await _service.upload_excel_in_background(background_tasks, await file.read())
        return Response(
            message="Employees are uploading, It will take sometime..",
            success=True,
            status=ResponseStatus.CREATED,
            data=result,
        )
        
        
@router.get("/roles/all/", response_model=Response[List[RoleResponse]])
async def get_all_users_by_role(
    filters : Optional[str] = None,
    sort : Optional[str] = None,
    user_service: UserService = Depends(get_user_service),
):
    user_department = await user_service.get_all_users_by_role(filters, sort)
    return Response(
        message="User department fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user_department,
    )
    
@router.patch("/{user_id}", status_code=status.HTTP_200_OK)
async def update_user_department(
    user_id: UUID,
    request: UpdateUserRequest,
    user_service: UserService = Depends(get_user_service),
):
    user_department = await user_service.update_user(user_id, request)    
    return Response(
        message="User department updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=user_department,
    )