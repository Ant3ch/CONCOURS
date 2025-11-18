import asyncio
import time
import os
import sqlite3
from classes.User import User

# will manage differents instances of User class to centralize actions
class InstanceManager:
    def __init__(self):
        self.users = []
        root_dir = os.path.dirname(os.path.dirname(__file__))  # project root
        self.db_path = os.path.join(root_dir, "database.db")
        self.conn = sqlite3.connect(self.db_path)
        self._setup_db()
        return

    def _setup_db(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                idUser INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seen (
                idSeen VARCHAR(50) PRIMARY KEY
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS userSeen (
                idUser INTEGER,
                idSeen VARCHAR(50),
                PRIMARY KEY (idUser, idSeen),
                FOREIGN KEY (idUser) REFERENCES users(idUser),
                FOREIGN KEY (idSeen) REFERENCES seen(idSeen)
            );
        """)
        self.conn.commit()

    async def add_user(self, user):
        user.attach_db(self.conn)
        self.users.append(user)

    async def getusers(self):
        return self.users
    async def loginAll(self):
        print(f"🔐 Logging in {len(self.users)} users...")
        tasks = [asyncio.create_task(u.login()) for u in self.users]
        await asyncio.gather(*tasks)

    async def closeAll(self):
        for u in self.users:
            user : User = u
            await user.close()
        try:
            self.conn.close()
        except:
            pass

    async def scanAll(self):
        tasks = [asyncio.create_task(u.run()) for u in self.users]
        await asyncio.gather(*tasks)

            
    async def shutdown(self):
        for u in self.users:
            await u.close()
        self.users.clear()
        try:
            self.conn.close()
        except:
            pass
