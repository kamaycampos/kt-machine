# Connect Instagram + Facebook: posting and comment → DM

**With your computer connected ([SETUP_COMPUTER.md](SETUP_COMPUTER.md)), your Claude does every step below in your browser. You only log in and click "Continue as…".** Without it, it takes about 20 minutes once: type `post` in Claude and it walks you through this page one step at a time. This page is for when you want to see every click. **You** = a click only you can make. **Claude** = Claude does it for you.

## 1. Instagram becomes a Professional account (2 min). You:
1. Open the Instagram app → your profile → **☰** (top right) → **Settings and activity**
2. **Account type and tools** → **Switch to professional account**
3. Choose **Creator** (or **Business**) and pick any category. It's free, and nothing about your account is lost.

## 2. Link Instagram to a Facebook Page (2 min). You:
1. No Facebook Page yet? Go to facebook.com → **Menu** → **Page** → **Create new Page**. Use your name or brand.
2. On the Page: **Settings** → **Linked accounts** → **Instagram** → **Connect account**, then log in to Instagram.

## 3. Let tools read your messages (30 sec). You:
In the Instagram app: **Settings and activity** → **Messages and story replies** → **Message controls** → turn on **Allow access to messages**. Without this, Meta blocks every automatic DM.

## 4. Create your free Meta app (4 min). You:
1. Go to **developers.facebook.com** and log in with the Facebook account that runs your Page. Click **Get started** if asked, and accept.
2. **My Apps** → **Create app** → choose **Other** → **Business** → name it, e.g. `My Factory` → **Create app**.
3. In the app: **App settings → Basic**. Copy the **App ID** and **App secret** (click Show), and paste both to Claude.

Your app stays in development mode, which is enough to post and send DMs on accounts you own. Meta's App Review is not needed.

## 5. Get your token (3 min). You click, Claude does the rest:
1. Open **developers.facebook.com/tools/explorer**
2. Top right: **Meta App** → choose your app. **User or Page** → **Get User Access Token**
3. Tick these permissions:
   `pages_show_list`, `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts`, `pages_manage_engagement`, `pages_messaging`, `publish_video`, `business_management`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `instagram_manage_insights`, `instagram_manage_messages`
4. **Generate Access Token** → continue as yourself → select your Page and your Instagram → **Save**
5. Copy the token at the top and paste it to Claude.

**Claude** then:
- turns it into a long-lived token (`oauth/access_token?grant_type=fb_exchange_token`)
- gets your **Page token**, which does not expire (`/me/accounts`)
- finds your Page ID and Instagram account ID (`/{page}?fields=instagram_business_account`)
- checks all of it with one test call

## 6. Paste five secrets and two variables (3 min). You:
Go to your repository → **Settings** → **Secrets and variables** → **Actions**.

**Secrets** tab → **New repository secret**, one at a time. Claude gives you each value:

| Name | Value |
|---|---|
| `IG_USER_ID` | your Instagram account ID |
| `IG_ACCESS_TOKEN` | your Page token |
| `FB_PAGE_ID` | your Page ID |
| `FB_ACCESS_TOKEN` | your Page token (the same one) |
| `KT_CTA_KEYWORDS` | your keyword(s), e.g. `KT,BRAIN` |

**Variables** tab → **New repository variable**:

| Name | Value |
|---|---|
| `DM_AUTO` | `on` |
| `AUTOPOST` | `on`, when you want posting automatic too |

## 7. Test it (2 min)
1. From a **second** account (a friend's, or your personal one), comment your keyword, e.g. `KT`, on one of your posts.
2. In your repository → **Actions** → **post** → **Run workflow**. Or wait up to 20 minutes.
3. The second account receives your link by DM. Your control panel's **Messages** room shows **1 sent**.

You can't test with your own account: Meta does not let a Page message itself. If nothing arrives, open **Messages** in the panel. It shows Meta's exact error, and Claude fixes it with you.

## Already using ManyChat or Meta's own auto-replies?
Keep one system, or people get two DMs. Either turn yours off, or leave `DM_AUTO` off.
