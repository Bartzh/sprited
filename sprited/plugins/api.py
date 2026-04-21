import jwt
import asyncio, uvicorn
import bcrypt
import os
import re
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from pydantic import BaseModel
from loguru import logger

from fastapi import FastAPI, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.websockets import WebSocketState
import msgpack

from pathlib import Path
import aiohttp
import aiosqlite
from webpush import WebPush, WebPushSubscription

from langchain_core.messages import AIMessage, HumanMessage

from sprited.plugin import *
from sprited import sprite_manager
from sprited.message import SpritedMsgMeta, convert_to_content_blocks, DEFAULT_AI_MSG_TYPE, DEFAULT_USER_MSG_TYPE
from sprited.tools.send_message import SEND_MESSAGE, SEND_MESSAGE_CONTENT

NAME = 'simple_api'

class ClientAuthFrame(BaseModel):
    type: Literal["auth"] = "auth"
    token: str

class ClientMessageFrame(BaseModel):
    type: Literal["message"] = "message"
    sprite_id: str
    content: str
    user_name: Optional[str] = None

class ClientPingFrame(BaseModel):
    type: Literal["ping"] = "ping"

class ClientInitFrame(BaseModel):
    type: Literal["init"] = "init"
    sprite_id: str

class ServerAuthResultFrame(BaseModel):
    type: Literal["auth_result"] = "auth_result"
    status: Literal["success", "error"]
    accessible_sprites: Optional[list[str]] = None
    detail: Optional[str] = None

class ServerInitFrame(BaseModel):
    type: Literal["init"] = "init"
    sprite_id: str
    messages: list[dict]

class ServerEventFrame(BaseModel):
    type: Literal["event"] = "event"
    event: dict

class ServerPongFrame(BaseModel):
    type: Literal["pong"] = "pong"

class ServerErrorFrame(BaseModel):
    type: Literal["error"] = "error"
    detail: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.user_queues: dict[str, asyncio.Queue] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            old_ws = self.active_connections[user_id]
            try:
                if old_ws.client_state != WebSocketState.DISCONNECTED:
                    await old_ws.close()
            except Exception:
                pass
        self.active_connections[user_id] = websocket
        self.user_queues[user_id] = asyncio.Queue()

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        self.user_queues.pop(user_id, None)

    async def send_msgpack(self, user_id: str, data: dict):
        websocket = self.active_connections.get(user_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await send_msgpack(websocket, data)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")

    def get_queue(self, user_id: str) -> Optional[asyncio.Queue]:
        return self.user_queues.get(user_id)

connection_manager = ConnectionManager()


async def send_msgpack(websocket: WebSocket, data: dict) -> None:
    await websocket.send_bytes(msgpack.packb(data, use_bin_type=True))

async def receive_msgpack(websocket: WebSocket) -> dict:
    return msgpack.unpackb(await websocket.receive_bytes(), raw=False)


app = FastAPI()


# 1. 捕获所有未处理的 Exception（500 错误）
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.opt(exception=exc).error("未处理的服务器异常: {}", str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

# 2. 捕获 HTTPException（如 404, 400 等）
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # 可选：只记录 5xx，或全部记录
    if exc.status_code >= 500:
        logger.error("HTTP 5xx 错误: {} {}", exc.status_code, exc.detail)
    else:
        logger.warning("客户端错误: {} {}", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# 3. 捕获请求验证错误（Pydantic）
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("请求参数校验失败: {}", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())}
    )



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")


# 用户数据文件路径
USERS_FILE = f"./config/{NAME}/users.json"
DEFAULT_USERS = {
    "default_user": {
        "password": "donotchangeifyouwantme",
        "is_admin": True,
        "accessible_sprites": [
            "default_sprite_1",
            "default_sprite_2",
            "default_sprite_3"
        ]
    }
}

if not os.path.exists(f"./config/{NAME}"):
    os.makedirs(f"./config/{NAME}")
if not os.path.exists(f"./data/{NAME}"):
    os.makedirs(f"./data/{NAME}")

def load_users_from_json() -> dict:
    """从 users.json 文件中加载用户信息，若文件不存在则创建空文件"""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump(DEFAULT_USERS, f, indent=4)
            return {}

    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


users_db = load_users_from_json()


private_key = os.getenv("API_PRIVATE_KEY", NAME)


@sprite_manager.on_sprite_output
async def on_sprite_output(**kwargs):
    sprite_id = kwargs['sprite_id']
    for user_id, queue in connection_manager.user_queues.items():
        if sprite_id in users_db[user_id]['accessible_sprites']:
            await queue.put(kwargs)


async def send_event_to_user(user_id: str, websocket: WebSocket):
    while True:
        try:
            queue = connection_manager.get_queue(user_id)
            if not queue:
                break
            event = await queue.get()
            if (
                event.get("is_self_call") and
                event.get("method") == "send_message" and
                not event.get("not_completed") and
                (user_sub := await get_user_subscriptions(user_id)) and
                (message_content := event.get("params", {}).get("content", ""))
            ):
                logger.info(f"Sending webpush message to {user_id}")
                message = wp.get(message=message_content, subscription=user_sub, ttl=600)
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        url=str(user_sub.endpoint),
                        data=message.encrypted,
                        headers=message.headers,
                    )
            await send_msgpack(websocket, {"type": "event", "event": event})
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Event sender error for {user_id}: {e}")
            break


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = None
    user_id = None
    event_task = None
    try:
        auth_data = await receive_msgpack(websocket)
        auth_frame = ClientAuthFrame.model_validate(auth_data)
        payload = verify_token(auth_frame.token)
        user_id = payload["sub"]
        connection_id = user_id + '_' + str(id(asyncio.current_task()))

        await connection_manager.connect(user_id, websocket)

        await send_msgpack(websocket, ServerAuthResultFrame(
            status="success",
            accessible_sprites=users_db[user_id]['accessible_sprites']
        ).model_dump())

        logger.info(f"WebSocket连接已建立: {connection_id}")

        event_task = asyncio.create_task(send_event_to_user(user_id, websocket))

        while True:
            try:
                data = await receive_msgpack(websocket)
                msg_type = data.get("type")

                if msg_type == "ping":
                    await send_msgpack(websocket, ServerPongFrame().model_dump())

                elif msg_type == "message":
                    sprite_id = data.get("sprite_id")
                    content = data.get("content", "")
                    user_name = data.get("user_name", None)
                    attachments = data.get("attachments", [])

                    try:
                        verify_sprite_accessible(user_id, sprite_id)
                    except HTTPException as e:
                        await send_msgpack(websocket, ServerErrorFrame(detail=e.detail).model_dump())
                        continue

                    extracted_messages = []
                    for attachment in attachments:
                        if attachment:
                            extracted_messages.extend(convert_to_content_blocks(attachment['content']))
                    extracted_messages.extend(convert_to_content_blocks(content))
                    if not extracted_messages:
                        await send_msgpack(websocket, ServerErrorFrame(detail="message is required").model_dump())
                        continue

                    is_admin = users_db[user_id].get('is_admin')
                    sprite_manager.call_sprite_for_user_with_command_nowait(
                        user_input=extracted_messages,
                        sprite_id=sprite_id,
                        is_admin=is_admin,
                        user_name=user_name
                    )

                elif msg_type == "init":
                    sprite_id = data.get("sprite_id")

                    try:
                        verify_sprite_accessible(user_id, sprite_id)
                    except HTTPException as e:
                        await send_msgpack(websocket, ServerErrorFrame(detail=e.detail).model_dump())
                        continue

                    await sprite_manager.init_sprite(sprite_id)
                    main_messages = await sprite_manager.main_graph.get_messages(sprite_id)
                    human_message_pattern = re.compile(r'^\[.*?\]\n.*?: ')
                    messages = []
                    for message in main_messages:
                        metadata = SpritedMsgMeta.parse(message)
                        if (
                            metadata.message_type != DEFAULT_USER_MSG_TYPE and
                            metadata.message_type != DEFAULT_AI_MSG_TYPE
                        ):
                            continue
                        elif isinstance(message, AIMessage):
                            for tool_call in message.tool_calls:
                                if tool_call["name"] == SEND_MESSAGE:
                                    if tool_call["args"].get(SEND_MESSAGE_CONTENT):
                                        messages.append({"role": "ai", "content": tool_call["args"][SEND_MESSAGE_CONTENT], "id": f'{message.id}.{tool_call["id"]}', "name": None})
                                    else:
                                        logger.warning(f'{SEND_MESSAGE}意外的没有参数，可能是打断导致的概率问题，也可能就是单纯的大模型输出错误')
                        elif isinstance(message, HumanMessage):
                            if isinstance(message.content, str):
                                content = human_message_pattern.sub('', message.text)
                                messages.append({"role": message.type, "content": content, "id": message.id, "name": message.name})
                            elif isinstance(message.content, list):
                                contents = message.content.copy()
                                for i, c in enumerate(contents):
                                    if isinstance(c, str):
                                        content = human_message_pattern.sub('', c)
                                        contents[i] = content
                                    elif isinstance(c, dict):
                                        if c.get("type") == "text" and isinstance(c.get("text"), str):
                                            content = human_message_pattern.sub('', c["text"])
                                            c_dict = c.copy()
                                            c_dict['text'] = content
                                            contents[i] = c_dict
                                messages.append({"role": message.type, "content": contents, "id": message.id, "name": message.name})
                        else:
                            messages.append({"role": message.type, "content": message.text, "id": message.id, "name": message.name})

                    await send_msgpack(websocket, ServerInitFrame(
                        sprite_id=sprite_id,
                        messages=messages
                    ).model_dump())

                else:
                    await send_msgpack(websocket, ServerErrorFrame(detail=f"Unknown message type: {msg_type}").model_dump())

            except WebSocketDisconnect:
                logger.info(f"WebSocket连接断开: {connection_id}")
                break
            except Exception as e:
                logger.exception(f"WebSocket错误: {connection_id}, {str(e)}")
                try:
                    await send_msgpack(websocket, ServerErrorFrame(detail=str(e)).model_dump())
                except Exception:
                    pass
                # 无论如何都要退出，避免死循环
                break

    except Exception as e:
        logger.error(f"WebSocket连接异常: {connection_id}, {str(e)}")
        try:
            if user_id:
                await connection_manager.send_msgpack(user_id, ServerErrorFrame(detail=str(e)).model_dump())
        except Exception:
            pass
    finally:
        if user_id:
            connection_manager.disconnect(user_id)
            if event_task:
                event_task.cancel()
        logger.info(f"WebSocket连接已关闭: {connection_id}")




# 生成 JWT 的函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm="HS256")
    return encoded_jwt

# 验证 JWT 的函数
def verify_token(token: str):
    try:
        payload = jwt.decode(token, private_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload['sub'] not in users_db.keys():
        raise HTTPException(status_code=400, detail="User not found")
    return payload

def verify_sprite_accessible(user_id: Optional[str] = None, sprite_id: Optional[str] = None):
    if not user_id:
        raise HTTPException(status_code=400, detail="User id is required")
    if not sprite_id:
        raise HTTPException(status_code=400, detail="sprite id is required")
    if user_id not in users_db.keys():
        raise HTTPException(status_code=400, detail="User not found")
    if sprite_id not in users_db[user_id]['accessible_sprites']:
        raise HTTPException(status_code=400, detail="sprite is not accessible")


@app.post("/api/login")
async def login(request: Request):
    r: dict = await request.json()
    username = r.get("username")
    u: dict = users_db.get(username)
    if not u:
        raise HTTPException(status_code=400, detail="User not found")
    pw: str = u.get("password")
    if not pw:
        raise HTTPException(status_code=400, detail="Password not found")
    hashedpassword: str = r.get("password")
    if not bcrypt.checkpw(pw.encode('utf-8'), hashedpassword.encode('utf-8')):
        logger.info("Incorrect username or password")
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": username}, expires_delta=timedelta(weeks=2))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/verify")
async def verify_route(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    return {"username": payload['sub']}



wp = WebPush(
    public_key=Path("./public_key.pem"),
    private_key=Path("./private_key.pem"),
    subscriber="admin@mail.com",
)


DATABASE_PATH = f"./data/{NAME}/users.sqlite"

async def init_db():
    """初始化数据库和表"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                subscription TEXT
            )
        """)
        await db.commit()

async def get_user_subscriptions(user_id: str) -> Optional[WebPushSubscription]:
    """从数据库获取用户的订阅"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT subscription FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                subscription = WebPushSubscription.model_validate(row[0])
                return subscription
            return None

async def save_subscription(user_id: str, subscription: WebPushSubscription):
    """保存用户的订阅到数据库，新订阅会替换旧订阅"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO users
            (user_id, subscription)
            VALUES (?, ?)
            """,
            (
                user_id,
                subscription.model_dump_json()
            )
        )
        await db.commit()

@app.get("/api/notification/key")
async def get_public_key(token: str = Depends(oauth2_scheme)):
    verify_token(token)
    if os.path.exists("./applicationServerKey"):
        with open("./applicationServerKey", "r") as f:
            return {"key": f.read()}
    raise HTTPException(status_code=404, detail="applicationServerKey not found")


@app.post("/api/notification/subscribe")
async def subscribe_user(subscription: WebPushSubscription, token: str = Depends(oauth2_scheme)):
    # global subscriptions
    payload = verify_token(token)
    user_id = payload['sub']

    # 保存订阅到数据库
    await save_subscription(user_id, subscription)

    return Response()




class SimpleAPI(BasePlugin):
    name = NAME
    server: uvicorn.Server | None = None
    server_task: asyncio.Task | None = None

    def __init__(self):
        self.server = None
        self.server_task = None

    async def on_manager_init(self) -> None:
        await init_db()
        config = uvicorn.Config(
            app=app,
            host=os.getenv('API_HOST', 'localhost'),
            port=int(os.getenv('API_PORT', 36262)),
            workers=1,
            timeout_keep_alive=10
        )
        self.server = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.server.serve())
        def on_task_done(task: asyncio.Task):
            try:
                task.result()
            except asyncio.CancelledError:
                pass
        self.server_task.add_done_callback(on_task_done)

    async def on_manager_close(self) -> None:
        if self.server:
            self.server.should_exit = True
        if self.server_task:
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        self.server = None
        self.server_task = None
