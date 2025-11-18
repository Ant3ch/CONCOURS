
from json import load
from classes.custom_types import usersList, User as UserType
from classes.InstanceManager import InstanceManager
from classes.User import User
from classes.Config import Config
from random import choice
import asyncio

#init users 
async def init_users(instance_manager:InstanceManager):
    users: usersList= await asyncio.to_thread(load, open("./users.json", "r", encoding="utf-8"))
    for k in users:
        user_k :UserType  = users[k]
        # add missing attributes respect to userType
        configuration = await (await Config(user_k).initialize()).to_dict()
        user = User(config = configuration)
        await user.initialize()
        await instance_manager.add_user(user)
        print(f"🚀 Launched {len(await instance_manager.getusers())} users.")
    
# scan hashtags for all users
async def main_loop():
    instance_manager =  InstanceManager()
    await init_users(instance_manager)

    await instance_manager.loginAll()
    while True:
        await instance_manager.scanAll()

asyncio.run(main_loop())

