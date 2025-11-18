from typing import TypedDict,List, Optional, Dict, NotRequired
from dotenv import load_dotenv,get_key
load_dotenv("../.env")

def _getv(key:str, env:str="../.env"):
    return get_key(key_to_get=key, dotenv_path=env)

class Credentials(TypedDict):
    username: str
    password: str
class ConfigDict(TypedDict):
    USERNAME: str
    PASSWORD: str
    WEBHOOK_URL: str
    DEV_MODE: bool
    AUTO_LIKE: bool
    AUTO_COMMENT: bool
    AUTO_FOLLOW: bool
    SEEN_DIR: str
    SEEN_FILE: str
    KEYWORDS: list[str]
    HASHTAGS: list[str]
    MENTIONS: NotRequired[list[str]]


class User(TypedDict):
    username: str
    password: str
    WEBHOOK_URL: NotRequired[str] = None
    DEV_MODE: NotRequired[bool]= False
    AUTO_LIKE: NotRequired[bool]=True
    AUTO_COMMENT: NotRequired[bool]=True
    AUTO_FOLLOW: NotRequired[bool] =True
    SEEN_DIR: NotRequired[str] = None
    SEEN_FILE: NotRequired[str] = None
    HASHTAGS: NotRequired[list[str]] = None
    KEYWORDS: NotRequired[list[str]] = None
    MENTIONS: NotRequired[list[str]] = None
    RESPONSES: NotRequired[list[str]] = None
class usersList(TypedDict):
    users: Dict[str, User]
