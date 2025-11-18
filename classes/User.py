import asyncio
import random
import requests
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import inspect

from classes.custom_types import ConfigDict
LIKE_SELECTOR = ".x1i10hfl.x972fbf.x10w94by.x1qhh985.x14e42zd.x9f619.x3ct3a4.xdj266r.x14z9mp.xat24cr.x1lziwak.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x6s0dn4.xjbqb8w.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl.x1ypdohk.x78zum5.xl56j7k.x1y1aw1k.xf159sx.xwib8y2.xmzvs34.xcdnw81.x1epzrsm.x1jplu5e.x14snt5h"
COMMENT_FORM_SELECTOR = ".x78zum5.x1q0g3np.x1iyjqo2.xs83m0k.xln7xf2.xk390pu.xvbhtw8.x1yvgwvq.xjd31um.x1ixjvfu.xwt6s21.x178xt8z.x1lun4ml.xso031l.xpilrb4.xum2pek.x1p2znge.xckx8r1.x12qyh8a.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl.xdj266r.x14z9mp.xat24cr.x1lziwak.x1y1aw1k.xf159sx.xwib8y2.xmzvs34"

class User:
    def __init__(self, config: ConfigDict):
        self.cfg = config
        self.driver = None
        self.username = self.cfg["USERNAME"]
        self.password = self.cfg["PASSWORD"]
        print(f"👤 User '{self.username}' initialized")
        # (DB is attached later by InstanceManager)

    def attach_db(self, conn: sqlite3.Connection):
        self.conn = conn
        self.user_id = self._get_or_create_user(self.username)
        print(f"👤 User '{self.username}' using shared DB (idUser={self.user_id})")

    def _get_or_create_user(self, username: str) -> int:
        self.conn.execute("INSERT OR IGNORE INTO users(username) VALUES (?)", (username,))
        self.conn.commit()
        cur = self.conn.execute("SELECT idUser FROM users WHERE username=?", (username,))
        return cur.fetchone()[0]

    async def initialize(self):
        await self._load_seen()
        await asyncio.wait_for(self._init_driver(), timeout=30)

    async def _init_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if not self.cfg["DEV_MODE"]:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    async def _load_seen(self):
        return  # deprecated

    def has_seen(self, sc: str) -> bool:
        if not hasattr(self, "conn"):
            raise RuntimeError("DB not attached to user")
        cur = self.conn.execute(
            "SELECT 1 FROM userSeen WHERE idUser=? AND idSeen=?",
            (self.user_id, sc)
        )
        return cur.fetchone() is not None

    def add_seen(self, sc: str):
        if not hasattr(self, "conn"):
            raise RuntimeError("DB not attached to user")
        try:
            self.conn.execute("INSERT OR IGNORE INTO seen(idSeen) VALUES (?)", (sc,))
            self.conn.execute("INSERT OR IGNORE INTO userSeen(idUser, idSeen) VALUES (?, ?)",
                              (self.user_id, sc))
            self.conn.commit()
        except Exception:
            pass

    async def save_seen(self):
        return  # no-op

    async def log(self, *a):
        if self.cfg["DEV_MODE"]:
            print(*a)

    async def login(self):
        self.driver.get("https://www.instagram.com/accounts/login/")
        await asyncio.sleep(3)
        try:
            u =  self.driver.find_element(By.NAME, "username")
            p = self.driver.find_element(By.NAME, "password")
            u.send_keys(self.username)
            p.send_keys(self.password)
            p.send_keys(Keys.ENTER)
            await asyncio.sleep(10)
            if "challenge" in self.driver.current_url.lower():
                code = input("2FA code: ")
                try:
                    ci = self.driver.find_element(By.NAME, "security_code")
                    ci.send_keys(code)
                    ci.send_keys(Keys.ENTER)
                    await asyncio.sleep(20)
                except:
                    input("Validate manually then press Enter: ")
            await self.log("[login] ok")
        except Exception as e:
            print("Login error:", e)
            self.driver.quit()
            raise

    async def send_discord(self, url, caption):
        payload = {"content": f"🎯 Concours détecté : {url}\n\n{caption[:200]}..."}
        try:
            r = requests.post(self.cfg["WEBHOOK_URL"], json=payload, timeout=10)
            await self.log("[discord]", r.status_code)
        except Exception as e:
            await self.log("Discord error:", e)
    
    async def build_comment(self):
        base = random.choice(self.cfg["RESPONSES"]).strip()
        mentions = " ".join(self.cfg["MENTIONS"]) if "MENTIONS" in self.cfg else ""
        return f"{base} {mentions}".strip()

    async def _poll_for(self, fn, timeout=15, interval=0.3):
        """Generic async poll helper."""
        end = asyncio.get_running_loop().time() + timeout
        while True:
            try:
                result = fn()
                if inspect.iscoroutine(result):
                    result = await result  # safety in case fn returns coroutine
                if result:
                    return result
            except Exception:
                pass
            if asyncio.get_running_loop().time() > end:
                return None
            await asyncio.sleep(interval)

    async def wait_for_css(self, selector, timeout=15):
        return await self._poll_for(
            lambda: self.driver.find_element(By.CSS_SELECTOR, selector),
            timeout=timeout
        )

    async def wait_for_clickable(self, selector, timeout=15):
        def _get():  # made sync (was async) to avoid returning coroutine
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                if el.is_displayed() and el.is_enabled():
                    return el
            except:
                return None
        return await self._poll_for(_get, timeout=timeout)

    async def like_current(self):
        try:
            btn = await self.wait_for_css(LIKE_SELECTOR, timeout=10)
            if not btn:
                await self.log("[like] btn not found")
                return False
            try:
                svg = btn.find_element(By.TAG_NAME, "svg")
            except:
                svgs = btn.find_elements(By.CSS_SELECTOR, "svg")
                svg = svgs[0] if svgs else None
            if not svg:
                for s in self.driver.find_elements(By.CSS_SELECTOR, "svg[aria-label]"):
                    label = (s.get_attribute("aria-label") or "").strip().lower()
                    if label in ("j’aime", "like"):
                        svg = s
                        try:
                            btn = s.find_element(By.XPATH, "./ancestor::button")
                        except:
                            pass
                        break
            if not svg:
                await self.log("[like] svg not found")
                return False
            aria = (svg.get_attribute("aria-label") or "").strip().lower()
            if aria in ("j’aime", "like"):
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                await asyncio.sleep(0.05)
                try:
                    btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", btn)
                await self.log("[like] done")
                return True
            await self.log("[like] already")
            return False
        except Exception as e:
            await self.log("[like] err", e)
            return False

    async def follow_current(self):
        if not self.cfg["AUTO_FOLLOW"]:
            return False
        try:
            candidates = self.driver.find_elements(By.CSS_SELECTOR,
                "div.x1i10hfl.xjqpnuy.xc5r6h4.xqeqjp1.x1phubyo.xdl72j9.x2lah0s.x3ct3a4.xdj266r.x14z9mp.xat24cr.x1lziwak.x2lwn1j.xeuugli.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1q0g3np.x1a2a7pz.x6s0dn4.xjyslct.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl.x9f619.x1ypdohk.x1f6kntn.xl56j7k.x17ydfre.x2b8uid.xlyipyv.x87ps6o.x14atkfc.x5c86q.x18br7mf.x1i0vuye")
            for c in candidates:
                t = c.text.strip().lower()
                if t == "suivre":
                    c.click()
                    await self.log("[follow] ok")
                    return True
                if t in ("suivi(e)", "abonné(e)"):
                    await self.log("[follow] already")
                    return False
            await self.log("[follow] not found")
            return False
        except Exception as e:
            await self.log("[follow] err", e)
            return False

    async def comment_current(self, retries=3):
        if not self.cfg["AUTO_COMMENT"]:
            return False
        text = await self.build_comment()
        selector_box = (
            "textarea.x1i0vuye.xgcd1z6.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl."
            "x5n08af.x78zum5.x1iyjqo2.x1qlqyl8.x1d6elog.xlk1fp6.x1a2a7pz."
            "xexx8yu.xyri2b.x18d9i69.x1c1uobl.xtt52l0.xnalus7.xs3hnx8."
            "x1bq4at4.xaqnwrm"
        )
        for attempt in range(retries):
            try:
                await asyncio.sleep(0.5)
                comment_box = await self.wait_for_clickable(selector_box, timeout=6)
                if not comment_box:
                    raise Exception("comment box timeout")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", comment_box)
                try:
                    comment_box.click()
                except:
                    self.driver.execute_script("arguments[0].click();", comment_box)
                try:
                    comment_box.clear()
                except:
                    pass
                comment_box.send_keys(text + " ")
                await asyncio.sleep(0.3)
                possible_send_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                    "div.x1i10hfl.xjqpnuy.xc5r6h4.xqeqjp1.x1phubyo.xdl72j9."
                    "x2lah0s.x3ct3a4.xdj266r.x14z9mp.xat24cr.x1lziwak.x2lwn1j."
                    "xeuugli.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1q0g3np.x1a2a7pz."
                    "x6s0dn4.xjyslct.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl."
                    "x9f619.x1ypdohk.x1f6kntn.xl56j7k.x17ydfre.x2b8uid.xlyipyv."
                    "x87ps6o.x14atkfc.x5c86q.x18br7mf.x1i0vuye.x11q7cde.xr5sc7."
                    "xf8g3cd.x20cjte.xt0b8zv.xjbqb8w.xr9e8f9.x1e4oeot.x1ui04y5."
                    "x6en5u8.x972fbf.x10w94by.x1qhh985.x14e42zd.xt0psk2.xt7dq6l."
                    "xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1n2onr6.x1n5bzlp")
                send_btn = next((b for b in possible_send_buttons if (b.text or "").strip().lower() in ("publier", "post")), None)
                if not send_btn:
                    raise Exception("send button not found")
                try:
                    send_btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", send_btn)
                await self.log("[comment] posted:", text)
                await asyncio.sleep(0.5)
                return True
            except Exception as e:
                await self.log(f"[comment] attempt {attempt+1} failed:", e)
        await self.log("[comment] failed")
        return False

    async def extract_caption(self):
        try:
            elems = self.driver.find_elements(By.CSS_SELECTOR, "h1, span[dir='auto'], article h1, div[role='dialog'] h1")
            txt = " ".join(e.text for e in elems if e.text).strip()
            if not txt:
                txt = self.driver.find_element(By.TAG_NAME, "body").text
            return txt.lower()
        except:
            return ""

    async def scan_hashtag(self, tag):
        await self.log("[scan]", tag)
        self.driver.get(f"https://www.instagram.com/explore/tags/{tag}/")
        first = await self.wait_for_css("a[href*='/p/'], a[href*='/reel/'], a[href*='/tv/']", timeout=12)
        if not first:
            await self.log("[scan] timeout", tag)
            return
        for _ in range(10):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(0.8)  # shorter delay -> more interleaving
            posts = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/'], a[href*='/tv/']")
            candidates = []
            for el in posts:
                link = el.get_attribute("href")
                if not link:
                    continue
                parts = [p for p in link.split("/") if p]
                if len(parts) < 2:
                    continue
                shortcode = parts[-1] if parts[-2] in ("p", "reel", "tv") else parts[-2]
                if self.has_seen(shortcode) or any(sc == shortcode for sc, _ in candidates):
                    continue
                candidates.append((shortcode, link))
            for sc, link in candidates:
                prev = set(self.driver.window_handles)
                self.driver.execute_script("window.open(arguments[0], '_blank');", link)
                await self._poll_for(lambda: len(set(self.driver.window_handles) - prev) > 0, timeout=5, interval=0.25)
                new_handles = list(set(self.driver.window_handles) - prev)
                if new_handles:
                    self.driver.switch_to.window(new_handles[0])
                else:
                    self.driver.get(link)
                await asyncio.sleep(1)
                if self.cfg["AUTO_LIKE"]: await self.like_current()
                if self.cfg["AUTO_FOLLOW"]: await self.follow_current()
                if self.cfg["AUTO_COMMENT"]: await self.comment_current()
                self.add_seen(sc)
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                await asyncio.sleep(0)  # yield to other users

    async def run(self):
        for tag in self.cfg["HASHTAGS"]:
            await self.scan_hashtag(tag)

    async def close(self):
        try:
            self.driver.quit()
        except:
            pass
        # Do not close shared DB connection here