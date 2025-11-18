import os
import json
from dotenv import load_dotenv, get_key
from classes.custom_types import User,ConfigDict

class Config:
    def __init__(self, userConfig: User, dotenv_path="./.env", dev_mode_override=None):
        if not load_dotenv(dotenv_path):
            print(f"❌ Warning: unable to load .env file at '{dotenv_path}'")
        self.dotenv_path = dotenv_path
        self.userConfig = userConfig
        self.dev_mode_override = dev_mode_override

    async def initialize(self):
        userConfig = self.userConfig
        dev_mode_override = self.dev_mode_override
        
        # Helpers for overrides
        async def _list_override(val):
            if val is None:
                return None
            if isinstance(val, (list, tuple, set)):
                return list(val)
            try:
                return list(eval(str(val)))
            except Exception:
                return None

        async def _bool_override(val):
            if val is None:
                return None
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes", "on")

        self.USERNAME = userConfig.get('USERNAME')
        self.PASSWORD = userConfig.get('PASSWORD')

        # SEEN_DIR override (userConfig key: seen_dir)
        uc_seen_dir =  userConfig.get('SEEN_DIR')
        self.SEEN_DIR = uc_seen_dir if uc_seen_dir else await self._get("SEEN_DIR", default="./seenFiles/")
        try:
            os.makedirs(self.SEEN_DIR, exist_ok=True)
        except Exception as e:
            print(f"❌ Unable to ensure seen dir '{self.SEEN_DIR}':", e)

        self.SEEN_FILE = await self._get_seen_file(self.USERNAME)

        # WEBHOOK_URL override
        self.WEBHOOK_URL = userConfig.get('WEBHOOK_URL') or await self._get("WEBHOOK_URL")

        # HASHTAGS
        uc_hashtags = await _list_override(userConfig.get('HASHTAGS'))
        self.HASHTAGS = uc_hashtags if uc_hashtags is not None else await self._eval_list("HASHTAGS", [])
        # KEYWORDS
        uc_keywords = await _list_override(userConfig.get('KEYWORDS'))
        self.KEYWORDS = uc_keywords if uc_keywords is not None else await self._eval_list("KEYWORDS", [])
        self.KEYWORDS.extend([k.capitalize() for k in list(self.KEYWORDS)])

        # MENTIONS
        uc_mentions = await _list_override(userConfig.get('MENTIONS'))
        raw_mentions = uc_mentions if uc_mentions is not None else await self._eval_list("MENTIONS", ["@letapisdallsuite", "@afton_fredbear"])
        self.MENTIONS = [m if m.startswith("@") else "@"+m for m in raw_mentions]

        # RESPONSES
        uc_responses =await _list_override(userConfig.get('RESPONSES'))
        self.RESPONSES = uc_responses if uc_responses is not None else await self._eval_list("RESPONSES", [
            "Super je participe !",
            "Bonne chance à tous !",
            "Trop cool 🔥",
            "Merci pour le concours !"
        ])

        # Booleans with override
        auto_like_uc = await _bool_override(userConfig.get('AUTO_LIKE'))
        self.AUTO_LIKE = auto_like_uc if auto_like_uc is not None else await self._bool(await self._get("AUTO_LIKE", default="true"))

        auto_comment_uc = await _bool_override(userConfig.get('AUTO_COMMENT'))
        self.AUTO_COMMENT = auto_comment_uc if auto_comment_uc is not None else await self._bool(await self._get("AUTO_COMMENT", default="true"))
        auto_follow_uc = await _bool_override(userConfig.get('AUTO_FOLLOW'))
        self.AUTO_FOLLOW = auto_follow_uc if auto_follow_uc is not None else await self._bool(await self._get("AUTO_FOLLOW", default="false"))

        # DEV_MODE
        dev_mode_uc = await _bool_override(userConfig.get('DEV_MODE'))
        env_dev = await self._bool(await self._get("DEV_MODE", default="false"))
        if dev_mode_override is not None:
            env_dev = bool(dev_mode_override)
        self.DEV_MODE = dev_mode_uc if dev_mode_uc is not None else env_dev
        return self

    # Remove broken creator; keep a no-op for compatibility if called elsewhere
    async def _create_seen_file_if_missing(self):
        # Deprecated: handled by SEEN_DIR creation above
        pass

    async def _get(self, key, default=None):
        try:
            v = get_key(key_to_get=key, dotenv_path=self.dotenv_path)
            if v is None:
                return default
            return v
        except Exception:
            return default

    async def _eval_list(self, key, default):
        raw = await self._get(key)
        if not raw:
            return default
        try:
            return list(eval(raw))
        except Exception:
            return default

    async def _bool(self, v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    async def _safe_name(self, s):
        s = s or "unknown"
        return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in s)

    async def seen_file_for(self, username):

        return os.path.join(self.SEEN_DIR, f"seen_{await self._safe_name(username)}.json")

    async def _get_seen_file(self, username):
        """Load seen file for given username; return list of seen post IDs. create it if not exists , default username_seen.json"""
        print("Seen dir:", self.SEEN_DIR)
        path = await self.seen_file_for(username)
        if not os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                print(f"❌ Unable to create seen file '{path}':", e)
                return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            print(f"❌ Unable to load seen file '{path}':", e)
            return []
            
        
    async def to_dict(self)->ConfigDict:
        return {
            "USERNAME": self.USERNAME,
            "PASSWORD": self.PASSWORD,
            "WEBHOOK_URL": self.WEBHOOK_URL,
            "DEV_MODE": self.DEV_MODE,
            "AUTO_LIKE": self.AUTO_LIKE,
            "AUTO_COMMENT": self.AUTO_COMMENT,
            "AUTO_FOLLOW": self.AUTO_FOLLOW,
            "SEEN_FILE": self.SEEN_FILE,
            "SEEN_DIR": self.SEEN_DIR,
            "KEYWORDS": self.KEYWORDS,
            "HASHTAGS": self.HASHTAGS,
            "MENTIONS": self.MENTIONS,
            "RESPONSES": self.RESPONSES
        }
