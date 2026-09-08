"""
Instagram Autoresponder for ANI (@ani.app.official)
Cloud Deployment Version (Render / Railway / VPS)
Runs 24/7 without proxy (direct cloud outbound to Meta Graph API).
"""

import os
import sys
import time
import json
import logging
import requests
from dotenv import load_dotenv

# Set UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("ANI_Cloud_Autoresponder")

load_dotenv()

PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("META_IG_ACCOUNT_ID", "17841473964245597")
APP_URL = os.getenv("APP_URL", "https://ani-app-official.web.app")

# Proxy is only needed if explicitly set
PROXY_HTTP = os.getenv("HTTP_PROXY")
PROXY_HTTPS = os.getenv("HTTPS_PROXY")
PROXIES = None
if PROXY_HTTP or PROXY_HTTPS:
    PROXIES = {
        "http": PROXY_HTTP,
        "https": PROXY_HTTPS
    }

PROCESSED_FILE = os.getenv("PROCESSED_FILE", "processed_comments.json")

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_processed(processed_set):
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_set), f, ensure_ascii=False, indent=2)

# German Triggers and Replies
TRIGGER_KEYWORDS = [
    "ani", "stil", "style", "kapsel", "capsule", "outfit", "app", 
    "kleiderschrank", "figur", "link", "wardrobe", "test", "demo", "info"
]

COMMENT_REPLY_TEXT = "Dein persönlicher Capsule-Link ist jetzt in unserer Bio! Tippe einfach auf den Link im Profil ✨👇"

def get_recent_media():
    url = f"https://graph.facebook.com/v22.0/{IG_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type,timestamp,comments_count",
        "limit": 10,
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        r = requests.get(url, params=params, proxies=PROXIES, timeout=30)
        if r.status_code == 200:
            return r.json().get("data", [])
        else:
            logger.error(f"Error fetching media: {r.status_code} {r.text}")
            return []
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return []

def get_media_comments(media_id):
    url = f"https://graph.facebook.com/v22.0/{media_id}/comments"
    params = {
        "fields": "id,text,username,timestamp,like_count",
        "limit": 25,
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        r = requests.get(url, params=params, proxies=PROXIES, timeout=30)
        if r.status_code == 200:
            return r.json().get("data", [])
        else:
            logger.error(f"Error fetching comments for {media_id}: {r.status_code} {r.text}")
            return []
    except Exception as e:
        logger.error(f"Request failed for comments {media_id}: {e}")
        return []

def reply_to_comment(comment_id, message):
    url = f"https://graph.facebook.com/v22.0/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        r = requests.post(url, json=payload, proxies=PROXIES, timeout=30)
        return r.status_code == 200, r.json()
    except Exception as e:
        return False, str(e)

def process_cycle(processed):
    media_list = get_recent_media()
    logger.info(f"Checking {len(media_list)} recent media items...")
    
    new_processed = False
    
    for media in media_list:
        comments_count = media.get("comments_count", 0)
        if comments_count == 0:
            continue
            
        media_id = media["id"]
        comments = get_media_comments(media_id)
        
        for comment in comments:
            cid = comment["id"]
            if cid in processed:
                continue
                
            text = comment.get("text", "").lower()
            username = comment.get("username", "anonymous")
            
            # Skip comments from the account itself
            if username.lower() in ("ani.app.official", "ani"):
                processed.add(cid)
                continue
            
            # Check trigger words or non-empty comments
            is_matched = any(kw in text for kw in TRIGGER_KEYWORDS) or len(text.strip()) > 0
            
            if is_matched:
                logger.info(f"Trigger matched for user @{username}: '{text}'")
                
                # Reply in comments
                reply_ok, reply_res = reply_to_comment(cid, f"@{username} {COMMENT_REPLY_TEXT}")
                if reply_ok:
                    logger.info(f"Successfully replied to comment {cid}")
                else:
                    logger.warning(f"Comment reply note: {reply_res}")
                
                processed.add(cid)
                new_processed = True
                
    if new_processed:
        save_processed(processed)

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"ANI Instagram Autoresponder is Running 24/7 OK\n")
    
    def log_message(self, format, *args):
        return  # suppress noisy health check logs

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check HTTP server listening on port {port}")
    server.serve_forever()

def main():
    logger.info("Starting ANI Cloud Instagram Autoresponder 24/7...")
    logger.info(f"Instagram Account ID: {IG_ACCOUNT_ID}")
    logger.info(f"App URL: {APP_URL}")
    
    if not PAGE_ACCESS_TOKEN:
        logger.error("META_PAGE_ACCESS_TOKEN is missing! Check environment variables.")
        sys.exit(1)
        
    # Start background web server for Render health check
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
        
    processed = load_processed()
    logger.info(f"Loaded {len(processed)} previously processed comments.")
    
    while True:
        try:
            process_cycle(processed)
        except Exception as e:
            logger.error(f"Error in cycle: {e}")
        time.sleep(25)  # Polling cycle 25 seconds

if __name__ == "__main__":
    main()
