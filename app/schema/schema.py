from pydantic import BaseModel, EmailStr


class SignupForm(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginForm(BaseModel):
    email: EmailStr
    password: str