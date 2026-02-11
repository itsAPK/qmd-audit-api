
from pydantic import BaseModel

from app.users.models import UserResponse


class Login(BaseModel):
    employee_id: str
    password: str
    
    
class ForgotPassword(BaseModel):
    employee_id: str
    
    
class ResetPassword(BaseModel):
    token: str
    password: str
    
class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str
    employee_id: str
    
    
class ChangePasswordRequest(BaseModel):
    new_password: str
    old_password: str
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse