"""
Instagram Autoresponder for ANI (@ani.app.official)
GitHub Actions Cron Version:
- Runs every 5-10 minutes via GitHub Actions schedule
- Checks recent Reels & posts for new comments
- Replies to comments with German bio link invite
- Saves processed comment IDs to a JSON file and commits it back to repo (cache persistence)
"""

import os
import sys
import json
import logging
import requests

# Set UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("ANI_GHA_Autoresponder")

PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("META_IG_ACCOUNT_ID", "17841473964245597")
APP_URL = os.getenv("APP_URL", "https://ani-app-official.web.app")

PROCESSED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_comments.json")

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
        json.dump(sorted(list(processed_set)), f, ensure_ascii=False, indent=2)

TRIGGER_KEYWORDS = [
    "ani", "stil", "style", "kapsel", "capsule", "outfit", "app", 
    "kleiderschrank", "figur", "link", "wardrobe", "test", "demo", "info"
]

COMMENT_REPLY_TEXT = "Dein persönlicher Capsule-Link ist jetzt in unserer Bio! Tippe einfach auf den Link im Profil ✨👇"

def get_recent_media():
    url = f"https://graph.facebook.com/v22.0/{IG_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type,timestamp,comments_count",
        "limit": 15,
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        r = requests.get(url, params=params, timeout=30)
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
        r = requests.get(url, params=params, timeout=30)
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
        r = requests.post(url, json=payload, timeout=30)
        return r.status_code == 200, r.json()
    except Exception as e:
        return False, str(e)

def run_once():
    logger.info("Starting ANI GitHub Actions Autoresponder run...")
    if not PAGE_ACCESS_TOKEN:
        logger.error("META_PAGE_ACCESS_TOKEN is missing!")
        sys.exit(1)

    processed = load_processed()
    logger.info(f"Loaded {len(processed)} previously processed comments.")
    
    media_list = get_recent_media()
    logger.info(f"Found {len(media_list)} recent media items.")
    
    new_replies_count = 0
    
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
            
            # Skip comments from ANI itself
            if username.lower() in ("ani.app.official", "ani"):
                processed.add(cid)
                continue
            
            is_matched = any(kw in text for kw in TRIGGER_KEYWORDS) or len(text.strip()) > 0
            
            if is_matched:
                logger.info(f"Trigger matched for @{username}: '{text}'")
                reply_ok, reply_res = reply_to_comment(cid, f"@{username} {COMMENT_REPLY_TEXT}")
                if reply_ok:
                    logger.info(f"Successfully replied to comment {cid}")
                    new_replies_count += 1
                else:
                    logger.warning(f"Reply error: {reply_res}")
                
                processed.add(cid)
                
    if new_replies_count > 0:
        logger.info(f"Made {new_replies_count} new replies. Saving state...")
        save_processed(processed)
        # Output indicator for GitHub Actions to commit changes
        print("::set-output name=has_changes::true")
    else:
        logger.info("No new comments to process.")
        print("::set-output name=has_changes::false")

if __name__ == "__main__":
    run_once()
