# Instructions for 24/7 Cloud Deployment (Render / Railway)

### Option 1: Render.com (100% Free Background Worker)
1. Go to **[render.com](https://dashboard.render.com)** -> Click **New +** -> **Background Worker** (or Web Service).
2. Connect your GitHub repository containing this `cloud_autoresponder` folder (or deploy via Git).
3. Set:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
4. Add **Environment Variables**:
   - `META_PAGE_ACCESS_TOKEN`: `<your_token>`
   - `META_IG_ACCOUNT_ID`: `17841473964245597`
   - `APP_URL`: `https://ani-app-official.web.app`

---

### Option 2: Railway.app (One-Click)
1. Go to **[railway.app](https://railway.app)** -> New Project.
2. Deploy from GitHub or Dockerfile.
3. Paste Environment Variables in Settings.
4. Auto-starts and runs 24/7.
