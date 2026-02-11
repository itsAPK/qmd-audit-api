from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.core.schemas import Response, ResponseStatus
from app.core.security import authenticate
from app.settings.models import (
    Company,
    CompanyRequest,
    CompanyResponse,
    Department,
    DepartmentRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
    Plant,
    PlantRequest,
    PlantResponse,
    PlantUpdateRequest,
)
from app.settings.dependencies import get_settings_service
from app.settings.services import SettingsService
router = APIRouter()


@router.post(
    "/companies", status_code=status.HTTP_201_CREATED, response_model=Response[Company]
)
async def create_company(
    request: CompanyRequest, settings_service: SettingsService = Depends(get_settings_service)
):

    company = await settings_service.create_company(request)

    return Response(
        message="Company created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=company,
    )


@router.get(
    "/companies", status_code=status.HTTP_200_OK, response_model=Response[list[CompanyResponse]]
)
async def get_all_companies(
    filters: str = None,
    sort: str = None,
    settings_service: SettingsService = Depends(get_settings_service)
):
    companies = await settings_service.get_all_companies(filters=filters, sort=sort)
    return Response(
        message="Companies fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=companies,
    )


@router.get(
    "/companies/{company_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[CompanyResponse],
)
async def get_company_by_id(
    company_id: UUID, settings_service: SettingsService = Depends(get_settings_service)
):
    company = await settings_service.get_company_by_id(company_id)
    return Response(
        message="Company fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=company,
    )


@router.patch(
    "/companies/{company_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[Company],
)
async def update_company(
    company_id: UUID,
    request: CompanyRequest,
    settings_service: SettingsService = Depends(get_settings_service),
):
    company = await settings_service.update_company(company_id, request)
    return Response(
        message="Company updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=company,
    )


@router.delete(
    "/companies/{company_id}", status_code=status.HTTP_200_OK, response_model=Response[bool]
)
async def delete_company(
    company_id: UUID, settings_service: SettingsService = Depends(get_settings_service)
):
    company = await settings_service.delete_company(company_id)
    return Response(
        message="Company deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )
    
@router.post(
    "/plants", status_code=status.HTTP_201_CREATED, response_model=Response[Plant]
)
async def create_plant(
    request: PlantRequest, settings_service: SettingsService = Depends(get_settings_service)
):

    plant = await settings_service.create_plant(request)

    return Response(
        message="Plant created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=plant,
    )


@router.get(
    "/plants", status_code=status.HTTP_200_OK, response_model=Response[list[PlantResponse]]
)
async def get_all_plants(
    filters: str = None,
    sort: str = None,
    settings_service: SettingsService = Depends(get_settings_service)
):
    plants = await settings_service.get_all_plants(filters=filters, sort=sort)
    return Response(
        message="Plants fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=plants,
    )


@router.get(
    "/plants/{plant_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[PlantResponse],
)
async def get_plant_by_id(
    plant_id: UUID, settings_service: SettingsService = Depends(get_settings_service)
):
    plant = await settings_service.get_plant_by_id(plant_id)
    return Response(
        message="Plant fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=plant,
    )


@router.patch(
    "/plants/{plant_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[Plant],
)
async def update_plant(
    plant_id: UUID,
    request: PlantUpdateRequest,
    settings_service: SettingsService = Depends(get_settings_service),
):
    plant = await settings_service.update_plant(plant_id, request)
    return Response(
        message="Plant updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=plant,
    )


@router.delete(
    "/plants/{plant_id}", status_code=status.HTTP_200_OK, response_model=Response[bool]
)
async def delete_plant(
    plant_id: UUID, settings_service: SettingsService = Depends(get_settings_service)
):
    plant = await settings_service.delete_plant(plant_id)
    return Response(
        message="Plant deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )
    
@router.post(
    "/departments", status_code=status.HTTP_201_CREATED, response_model=Response[Department]
)
async def create_department(
    request: DepartmentRequest, settings_service: SettingsService = Depends(get_settings_service)
):

    department = await settings_service.create_department(request)

    return Response(
        message="Department created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=department,
    )


@router.get(
    "/departments", status_code=status.HTTP_200_OK, response_model=Response[list[DepartmentResponse]]
)
async def get_all_departments(
    filters: str = None,
    sort: str = None,
    settings_service: SettingsService = Depends(get_settings_service)
):
    departments = await settings_service.get_all_departments(filters=filters, sort=sort)
    return Response(
        message="Departments fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=departments,
    )


@router.get(
    "/departments/{department_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[DepartmentResponse],
)
async def get_department_by_id(
    department_id: UUID, settings_service: SettingsService = Depends(get_settings_service)
):
    department = await settings_service.get_department_by_id(department_id)
    return Response(
        message="Department fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=department,
    )


@router.patch(
    "/departments/{department_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[Department],
)
async def update_department(
    department_id: UUID,
    request: DepartmentUpdateRequest,
    settings_service: SettingsService = Depends(get_settings_service),
):
    department = await settings_service.update_department(department_id, request)
    return Response(
        message="Department updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=department,
    )


@router.delete(
    "/departments/{department_id}", status_code=status.HTTP_200_OK, response_model=Response[bool]
)
async def delete_department(
    department_id: UUID, settings_service: SettingsService = Depends(get_settings_service), user = Depends(authenticate)
):
    department = await settings_service.delete_department(department_id)
    return Response(
        message="Department deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )
    
