from fastapi import APIRouter, HTTPException, status ,Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt,JWTError
from db.Modelos.Userdb import Userdb
from db.Modelos.User import User
from db.Schemas.Userdb import buscaUserdb,user_schema,users_schema
from db.cliente import client
from passlib.context import CryptContext
from datetime import datetime,timedelta
from bson import ObjectId

ALGORITM = "HS256"
ACCESS_TOKEN_DURATION = 5
SECRET = "1jkhdksdhk34k"
router = APIRouter(prefix= "/user",tags=["user"])
Oauth2 = OAuth2PasswordBearer(tokenUrl="user/login")
crypt = CryptContext(schemes=["bcrypt"])

async def auth_user(token: str = Depends(Oauth2)):
    exception = HTTPException(status_code= status.HTTP_401_UNAUTHORIZED,
                             detail= "Credenciales invalidas")
    try:
        username = jwt.decode(token, SECRET, algorithms= ALGORITM).get("sub")
        if username is None:
            raise exception
    except JWTError:
        raise exception
    return buscaUserdb("email",username)

async def current_user(user: User = Depends(auth_user)):
    user_dict = dict(user)
    if user_dict["disabled"]:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST,
                             detail= "Usuario inactivo")
    return user


@router.post("/register")
async def authUser(user: Userdb):
    if user is None:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED,
                            detail= "Usted no esta registrado como usuario")
    if type(buscaUserdb("email",user.email)) == User:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "El usuario ya existe")
    user_dict = dict(user)
    user_dict["password"] = crypt.hash(user_dict["password"])
    del user_dict["id"]
    id = client.users2.insert_one(user_dict).inserted_id
    return buscaUserdb("_id",id)

@router.get("/{id}")
async def getUser(id: str, user: User = Depends(current_user)):
    if user is None:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED,
                            detail= "Usted no esta registrado como usuario")
    return buscaUserdb("_id",ObjectId(id))
    


@router.post("/login")
async def authUser(form : OAuth2PasswordRequestForm = Depends()):
    user = client.users2.find_one({"email": form.username})
    try:
        user = Userdb(**user)
    except:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND,
                             detail= "Email no encontrado")
    if crypt.verify(form.password,user.password):
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_DURATION)
        access_token = {"sub": user.email, "exp": expire}
        return {"access_token": jwt.encode(access_token,SECRET,algorithm= ALGORITM),"token_type": "bearer"}
    else:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED,
                             detail= "Contraseña incorrecta")
    

    

@router.get("/me")
async def hola(user: User = Depends(current_user)):
        if user is None:
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST)
        return user
    
     
@router.patch("/password")
async def setPassword(newpass: str, user: User = Depends(current_user)):
    if user is None:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST)
    user_dict = dict(user)
    newpass = crypt.hash(newpass)
    try:
        client.users2.update_one({"email":user.email},{"$set": {"password": newpass}})
        return "Contraseña actualizada"
    except:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "Intente con otra contraseña")



@router.patch("/email",status_code= status.HTTP_202_ACCEPTED)
async def setEmail(newemail: str, user: User = Depends(current_user)):
    if user is None:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST)
    if type(buscaUserdb("email",newemail)) == User:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "El correo ya existe")
    try:
        client.users2.update_one({"email":user.email},{ "$set": {"email": newemail}})
        return buscaUserdb("email",newemail)
    except:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= "No se actualizo el usuario")
    