import json
import os
from typing import Dict, List, Optional
from models import AccountRecord, UserSession
from datetime import datetime, timedelta

DATA_FILE = "data.json"
SESSIONS_FILE = "sessions.json"


class Database:
    def __init__(self):
        self.accounts: List[Dict] = []
        self.sessions: Dict[str, UserSession] = {}
        self.load_data()

    def load_data(self):
        # 加载账户数据
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', [])
            except:
                self.accounts = []

        # 加载会话数据
        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    self.sessions = {}
                    for session_id, session_data in sessions_data.items():
                        # 检查会话是否过期（24小时）
                        login_time = datetime.fromisoformat(session_data['login_time'])
                        if datetime.now() - login_time < timedelta(hours=24):
                            self.sessions[session_id] = UserSession(**session_data)
            except:
                self.sessions = {}

    def save_data(self):
        # 保存账户数据
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({'accounts': self.accounts}, f, ensure_ascii=False, indent=2)

        # 保存会话数据
        sessions_data = {}
        for session_id, session in self.sessions.items():
            sessions_data[session_id] = session.dict()

        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)

    def get_all_accounts(self) -> List[Dict]:
        accounts = self.accounts.copy()
        # 计算每个账户的剩余金额（整数计算）
        for account in accounts:
            total_paid = sum(account['paid_amounts'])
            account['remaining_amount'] = account['total_amount'] - total_paid
        return accounts

    def add_account(self, account: AccountRecord):
        account_dict = account.dict()
        self.accounts.append(account_dict)
        self.save_data()

    def update_account(self, index: int, account_data: Dict):
        if 0 <= index < len(self.accounts):
            self.accounts[index] = account_data
            self.save_data()

    def delete_account(self, index: int):
        if 0 <= index < len(self.accounts):
            self.accounts.pop(index)
            self.save_data()

    def add_paid_amount(self, index: int, amount: int):
        if 0 <= index < len(self.accounts):
            self.accounts[index]['paid_amounts'].append(amount)
            self.save_data()

    def toggle_lock(self, index: int, locked: bool):
        if 0 <= index < len(self.accounts):
            self.accounts[index]['locked'] = locked
            self.save_data()

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            login_time = datetime.fromisoformat(session.login_time)
            if current_time - login_time >= timedelta(hours=24):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]

        if expired_sessions:
            self.save_data()


# 全局数据库实例
db = Database()