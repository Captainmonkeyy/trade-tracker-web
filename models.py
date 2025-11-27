from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class AccountRecord(BaseModel):
    account_code: str
    account_name: str
    total_amount: int
    manager: str
    created_time: str
    paid_amounts: List[int] = []
    locked: bool = False

class UserSession(BaseModel):
    username: str
    is_viewer: bool = False
    login_time: str

# 账户编码映射数据库
ACCOUNT_MAPPING = {
    "1243": "泰康资产XX年金",
    "1001": "平安保险养老金",
    "1002": "国寿投资专户",
    "1003": "太保资管组合",
    "1004": "新华保险投资户",
    "1005": "人保资产专项",
    "1006": "太平养老组合",
    "1007": "华泰资产产品",
    "1008": "安邦保险投资",
}