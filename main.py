from fastapi import FastAPI, Request, Form, HTTPException, Cookie, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
import uuid
from datetime import datetime, timedelta
from typing import Optional

from models import AccountRecord, UserSession, ACCOUNT_MAPPING
from database import db

app = FastAPI(title="账户管理系统")

# 模板和静态文件配置
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_session(session_id: Optional[str] = None) -> Optional[UserSession]:
    if session_id and session_id in db.sessions:
        session = db.sessions[session_id]
        # 检查会话是否过期
        login_time = datetime.fromisoformat(session.login_time)
        if datetime.now() - login_time < timedelta(hours=24):
            return session
        else:
            # 删除过期会话
            del db.sessions[session_id]
            db.save_data()
    return None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session_id: Optional[str] = Cookie(None)):
    # 清理过期会话
    db.cleanup_expired_sessions()

    session = get_session(session_id)

    # 如果没有会话或会话过期，重定向到登录页面
    if not session:
        response = templates.TemplateResponse("login.html", {"request": request})
        # 清除可能存在的过期cookie
        response.delete_cookie("session_id")
        return response

    accounts = db.get_all_accounts()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "session": session,
        "accounts": accounts,
        "account_mapping": ACCOUNT_MAPPING
    })


@app.post("/login")
async def login(request: Request, response: Response, username: str = Form(""), viewer_mode: bool = Form(False)):
    session_id = str(uuid.uuid4())

    if viewer_mode:
        session = UserSession(username="浏览者", is_viewer=True, login_time=datetime.now().isoformat())
    else:
        if not username.strip():
            # 如果用户名为空，停留在登录页面并显示错误
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "请输入用户名"
            })
        session = UserSession(username=username.strip(), login_time=datetime.now().isoformat())

    db.sessions[session_id] = session
    db.save_data()

    redirect_response = RedirectResponse(url="/", status_code=303)
    # 设置Cookie，有效期24小时
    redirect_response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=24 * 60 * 60  # 24小时
    )
    return redirect_response


@app.post("/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    if session_id and session_id in db.sessions:
        del db.sessions[session_id]
        db.save_data()

    redirect_response = RedirectResponse(url="/", status_code=303)
    redirect_response.delete_cookie("session_id")
    return redirect_response


@app.post("/add_account")
async def add_account(
        request: Request,
        account_code: str = Form(...),
        total_amount: int = Form(...),
        session_id: Optional[str] = Cookie(None)
):
    session = get_session(session_id)
    if not session or session.is_viewer:
        raise HTTPException(status_code=403, detail="浏览模式无法添加账户")

    if account_code not in ACCOUNT_MAPPING:
        raise HTTPException(status_code=400, detail="无效的账户编码")

    account = AccountRecord(
        account_code=account_code,
        account_name=ACCOUNT_MAPPING[account_code],
        total_amount=total_amount,
        manager=session.username,
        created_time=datetime.now().isoformat()
    )

    db.add_account(account)
    return RedirectResponse(url="/", status_code=303)


@app.post("/add_payment/{account_index}")
async def add_payment(
        account_index: int,
        amount: int = Form(...),
        session_id: Optional[str] = Cookie(None)
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="未登录")

    accounts = db.get_all_accounts()
    if account_index < 0 or account_index >= len(accounts):
        raise HTTPException(status_code=404, detail="账户不存在")

    account = accounts[account_index]

    # 检查是否被锁定
    if account['locked'] and account['manager'] != session.username:
        raise HTTPException(status_code=403, detail="账户已被锁定")

    total_paid = sum(account['paid_amounts'])
    remaining = account['total_amount'] - total_paid

    if amount > remaining:
        raise HTTPException(status_code=400, detail="支付金额超过剩余金额")

    db.add_paid_amount(account_index, amount)
    return RedirectResponse(url="/", status_code=303)


@app.post("/toggle_lock/{account_index}")
async def toggle_lock(account_index: int, session_id: Optional[str] = Cookie(None)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="未登录")

    accounts = db.get_all_accounts()
    if account_index < 0 or account_index >= len(accounts):
        raise HTTPException(status_code=404, detail="账户不存在")

    account = accounts[account_index]

    # 只有管理人才能锁定/解锁
    if account['manager'] != session.username:
        raise HTTPException(status_code=403, detail="只能操作自己的账户")

    new_lock_state = not account['locked']
    db.toggle_lock(account_index, new_lock_state)
    return RedirectResponse(url="/", status_code=303)


@app.post("/delete_account/{account_index}")
async def delete_account(account_index: int, session_id: Optional[str] = Cookie(None)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="未登录")

    accounts = db.get_all_accounts()
    if account_index < 0 or account_index >= len(accounts):
        raise HTTPException(status_code=404, detail="账户不存在")

    account = accounts[account_index]

    # 只有管理人才能删除
    if account['manager'] != session.username and not session.is_viewer:
        raise HTTPException(status_code=403, detail="只能删除自己的账户")

    db.delete_account(account_index)
    return RedirectResponse(url="/", status_code=303)


@app.get("/get_account_name/{account_code}")
async def get_account_name(account_code: str):
    if account_code in ACCOUNT_MAPPING:
        return {"account_name": ACCOUNT_MAPPING[account_code]}
    else:
        raise HTTPException(status_code=404, detail="账户编码不存在")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)