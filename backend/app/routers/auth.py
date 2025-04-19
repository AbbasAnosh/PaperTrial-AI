from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class GoogleAuthRequest(BaseModel):
    token: str

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_service = AuthService()
    result = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "access_token": result["token"],
        "token_type": "bearer",
        "user": result["user"]
    }

@router.post("/google", response_model=Token)
async def google_auth(request: GoogleAuthRequest):
    auth_service = AuthService()
    try:
        result = await auth_service.authenticate_google(request.token)
        return {
            "access_token": result["token"],
            "token_type": "bearer",
            "user": result["user"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    auth_service = AuthService()
    try:
        payload = auth_service.verify_token(token)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) 