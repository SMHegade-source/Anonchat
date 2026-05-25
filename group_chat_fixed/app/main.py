from fastapi import FastAPI, Depends, Request, WebSocket, WebSocketDisconnect, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from . import models, schemas, database, utils, websocket
import json

print("Creating database tables...")
models.Base.metadata.create_all(bind=database.engine)
print("Database tables created.")

app = FastAPI(title="Anonymous Group Chat")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key-for-development")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()

@app.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def post_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})
    
    hashed_pw = utils.get_password_hash(password)
    # Generate unique anonymous username
    while True:
        username = utils.generate_anonymous_username()
        if not db.query(models.User).filter(models.User.username == username).first():
            break
            
    new_user = models.User(email=email, password_hash=hashed_pw, username=username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    request.session["user_id"] = new_user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not utils.verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})
    
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        
    groups = db.query(models.Group).all()
    # Find which groups the user has joined/requested
    memberships = db.query(models.GroupMember).filter(models.GroupMember.user_id == user.id).all()
    membership_map = {m.group_id: m.status for m in memberships}
    
    response = templates.TemplateResponse("index.html", {
        "request": request, 
        "groups": groups, 
        "username": user.username,
        "membership_map": membership_map,
        "user_id": user.id
    })
    return response

@app.post("/create_group")
async def create_group(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    new_group = models.Group(name=name, description=description, tags=tags, owner_id=user.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    # Auto-approve the owner
    membership = models.GroupMember(group_id=new_group.id, user_id=user.id, status="approved")
    db.add(membership)
    db.commit()
    
    return RedirectResponse(url=f"/group/{new_group.id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/join_group/{group_id}")
async def join_group(request: Request, group_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        
    # Check if already a member/pending
    existing = db.query(models.GroupMember).filter(
        models.GroupMember.group_id == group_id, 
        models.GroupMember.user_id == user.id
    ).first()
    
    if not existing:
        new_req = models.GroupMember(group_id=group_id, user_id=user.id, status="pending")
        db.add(new_req)
        db.commit()
        
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/approve_join/{request_id}")
async def approve_join(request: Request, request_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        
    membership = db.query(models.GroupMember).filter(models.GroupMember.id == request_id).first()
    if not membership:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    group = db.query(models.Group).filter(models.Group.id == membership.group_id).first()
    if group.owner_id == user.id:
        membership.status = "approved"
        db.commit()
        
    return RedirectResponse(url=f"/group/{group.id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/group/{group_id}", response_class=HTMLResponse)
async def read_group(request: Request, group_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    membership = db.query(models.GroupMember).filter(
        models.GroupMember.group_id == group_id, 
        models.GroupMember.user_id == user.id
    ).first()
    
    if not membership or membership.status != "approved":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    messages = db.query(models.Message).filter(models.Message.group_id == group_id).order_by(models.Message.timestamp.asc()).all()
    
    # If user is owner, get pending requests
    pending_requests = []
    if group.owner_id == user.id:
        pending_requests = db.query(models.GroupMember, models.User).join(models.User).filter(
            models.GroupMember.group_id == group_id,
            models.GroupMember.status == "pending"
        ).all()
        
    response = templates.TemplateResponse("group.html", {
        "request": request, 
        "group": group, 
        "messages": messages, 
        "username": user.username,
        "is_owner": group.owner_id == user.id,
        "pending_requests": pending_requests
    })
    return response

@app.websocket("/ws/{group_id}/{username}")
async def websocket_endpoint(websocket_conn: WebSocket, group_id: int, username: str):
    await websocket.manager.connect(websocket_conn, group_id)
    try:
        while True:
            data = await websocket_conn.receive_text()
            db = database.SessionLocal()
            try:
                new_message = models.Message(group_id=group_id, username=username, content=data)
                db.add(new_message)
                db.commit()
            finally:
                db.close()
            
            message_data = {
                "username": username,
                "content": data
            }
            await websocket.manager.broadcast(json.dumps(message_data), group_id)
            
    except WebSocketDisconnect:
        websocket.manager.disconnect(websocket_conn, group_id)
