from modules.usuario.domain.repositories.blacklist_repository import IBlacklistRepository

import redis
import time

import os
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")

r = redis.Redis(host=str(REDIS_HOST), port=int(REDIS_PORT), db=int(REDIS_DB))

class BlacklistRepository(IBlacklistRepository):
    def __init__(self):
        self.blacklist = set()

    def add_token(self, jti: str, exp: int):
        ttl = exp - int(time.time())
        if ttl > 0:
            r.setex(f"blacklist:{jti}", ttl, "true")
        
    def is_blacklisted(self, jti: str) -> bool:
        return r.exists(f"blacklist:{jti}") == 1
        