from typing import Optional
from app.settings.models import Company, CompanyRequest, CompanyResponse, CompanyUpdateRequest, Department, DepartmentRequest, DepartmentResponse, DepartmentUpdateRequest, Plant, PlantRequest, PlantResponse, PlantUpdateRequest
from sqlalchemy.orm import selectinload
from sqlmodel import select
from fastapi import HTTPException, status
from uuid import UUID

from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph


class SettingsService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build([Company, Plant, Department])

    async def create_company(self, request: CompanyRequest):

        company = Company(
            name=request.name,
            code=request.code,
        )
        self.session.add(company)
        await self.session.commit()
        return company

    async def get_all_companies(
        self, filters: Optional[str] = None, sort: Optional[str] = None
    ):
        stmt = select(Company).options(selectinload(Company.plants).options(selectinload(Plant.departments)))
        if filters:
            stmt = apply_filters(stmt, filters, Company, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Company, self.graph)

        result = await self.session.execute(stmt)
        companies = result.scalars().all()
        print(companies)
        return [
            CompanyResponse(
                id=company.id,
                name=company.name,
                code=company.code,
                plants=[
                    PlantResponse(
                        id=plant.id,
                        name=plant.name,
                        code=plant.code,
                        company_id=plant.company_id,
                        departments=[
                            DepartmentResponse(
                                id=department.id,
                                name=department.name,
                                code=department.code,
                                slug=department.slug,
                                plant_id=department.plant_id,
                            )
                            for department in plant.departments
                        ],
                    )
                    for plant in company.plants
                ],
            )
            for company in companies
        ]

    async def get_company_by_id(self, company_id: UUID):
        company = await self.session.execute(
            select(Company)
            .where(Company.id == company_id)
            .options(selectinload(Company.plants))
        )
        company = company.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Company not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return CompanyResponse(
            id=company.id,
            name=company.name,
            code=company.code,
            plants=[
                PlantResponse(
                    id=plant.id,
                    name=plant.name,
                    code=plant.code,
                    company_id=company.id,
                )
                for plant in company.plants
            ],
        )

    async def update_company(self, company_id: UUID, request: CompanyUpdateRequest):
        company = await self.session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company.scalar_one_or_none()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Company not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        company.name = request.name
        company.code = request.code
        await self.session.commit()
        return company

    async def delete_company(self, company_id: UUID):
        company = await self.session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company.scalar_one_or_none()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Company not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(company)
        await self.session.commit()
        return company
    
    
    async def create_plant(self, request: PlantRequest):
        plant = Plant(
            name=request.name,
            code=request.code,
            company_id=request.company_id,
        )
  
        self.session.add(plant)
        await self.session.commit()
        return plant

    async def get_all_plants(
        self, filters: Optional[str] = None, sort: Optional[str] = None
    ):
        stmt = select(Plant).options(selectinload(Plant.company))
        if filters:
            stmt = apply_filters(stmt, filters, Plant, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Plant, self.graph)

        result = await self.session.execute(stmt)
        plants = result.scalars().all()
        return [
            PlantResponse(
                id=plant.id,
                name=plant.name,
                code=plant.code,
                company_id=plant.company_id,
                company=CompanyResponse(
                    id=plant.company_id,
                    name=plant.company.name,
                    code=plant.company.code,
                ),
            )
            for plant in plants
        ]

    async def get_plant_by_id(self, plant_id: UUID):
        plant = await self.session.execute(
            select(Plant)
            .where(Plant.id == plant_id)
            .options(selectinload(Plant.company),selectinload(Plant.departments))
        )
        plant = plant.scalar_one_or_none()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Plant not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return PlantResponse(
            id=plant.id,
            name=plant.name,
            code=plant.code,
            company_id=plant.company_id,
            company=CompanyResponse(
                id=plant.company_id,
                name=plant.company.name,
                code=plant.company.code,
            ),
            departments=[
                DepartmentResponse(
                    id=department.id,
                    name=department.name,
                    code=department.code,
                    slug=department.slug,
                    plant_id=department.plant_id,
                  
                )
                for department in plant.departments
            ],
        )

    async def update_plant(self, plant_id: UUID, request: PlantUpdateRequest):
        plant = await self.session.execute(
            select(Plant).where(Plant.id == plant_id)
        )
        plant = plant.scalar_one_or_none()

        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Plant not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        plant.name = request.name
        plant.code = request.code
        await self.session.commit()
        return plant

    async def delete_plant(self, plant_id: UUID):
        plant = await self.session.execute(
            select(Plant).where(Plant.id == plant_id)
        )
        plant = plant.scalar_one_or_none()

        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Plant not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(plant)
        await self.session.commit()
        return plant
    
    
    async def create_department(self, request: DepartmentRequest):
        plant = await self.get_plant_by_id(request.plant_id)
        slug = plant.company.code + "-" + plant.code + "-" + request.code
        department = Department(
            name=request.name,
            code=request.code,
            slug=slug,
            plant_id=request.plant_id,
        )
      
        self.session.add(department)
        await self.session.commit()
        return department

    async def get_all_departments(
        self, filters: Optional[str] = None, sort: Optional[str] = None
    ):
        stmt = select(Department).options(selectinload(Department.plant))
        if filters:
            stmt = apply_filters(stmt, filters, Department, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Department, self.graph)

        result = await self.session.execute(stmt)
        departments = result.scalars().all()
        return [
            DepartmentResponse(
                id=department.id,
                name=department.name,
                code=department.code,
                slug=department.slug,
                plant_id=department.plant_id,
                plant=PlantResponse(
                    id=department.plant_id,
                    name=department.plant.name,
                    code=department.plant.code,
                    company_id=department.plant.company_id,
                ),
            )
            for department in departments
        ]
        
    async def get_department_by_id(self, department_id: UUID):
        department = await self.session.execute(
            select(Department)
            .where(Department.id == department_id)
            .options(selectinload(Department.plant))
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
        return DepartmentResponse(
            id=department.id,
            name=department.name,
            code=department.code,
            slug=department.slug,
            plant_id=department.plant_id,
            plant=PlantResponse(
                id=department.plant_id,
                name=department.plant.name,
                code=department.plant.code,
                company_id=department.plant.company_id,
            ),
        )

    async def update_department(self, department_id: UUID, request: DepartmentUpdateRequest):
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
            
        
        department.name = request.name
        department.code = request.code
        plant = await self.get_plant_by_id(department.plant_id)
        department.slug = plant.company.code + "-" + plant.code + "-" + request.code


        await self.session.commit()
        return department

    async def delete_department(self, department_id: UUID):
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
        await self.session.delete(department)
        await self.session.commit()
        return department