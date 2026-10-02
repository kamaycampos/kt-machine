# AUTOPILOT: connect your accounts (optional)

Studio mode already makes your clips and schedules them. Autopilot posts them for you. Type `post` and your Claude walks you through this page one step at a time, so you never have to read it all.

Each platform is separate. Connect one, switch autopilot on, and add the next whenever you like.

| Platform | Time | What you get |
|---|---|---|
| Instagram + Facebook | ~20 min, one setup covers both | Reels and Stories posted fully automatically |
| YouTube | ~15 min + a one-time Google review | Shorts posted automatically with covers |
| TikTok | ~15 min | Each clip lands in your TikTok drafts with its caption; you tap **Post** |

## Instagram + Facebook (Meta)
You need:
- an Instagram **Professional** account (Creator or Business), linked to a Facebook **Page**
- a free Meta developer app, which you create at [developers.facebook.com](https://developers.facebook.com) → My Apps → Create App → **Business**

It never needs Meta's App Review, because it only posts to your own accounts.

Your Claude gets your Page token with you in the Graph API Explorer and turns it into a **permanent** one. You then paste four secrets:
- `IG_USER_ID`
- `IG_ACCESS_TOKEN`
- `FB_PAGE_ID`
- `FB_ACCESS_TOKEN`

## YouTube
You need a free Google Cloud project with **YouTube Data API v3** turned on, and an OAuth client. Your Claude gets the refresh token with you in Google's OAuth Playground. You then paste three secrets:
- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`

**Publish** the OAuth consent screen to Production. In Testing mode the token dies after 7 days.

**One-time review:** Google keeps uploads from a brand-new API project private until the project passes the free YouTube API audit (a form, usually days to a few weeks). Your Claude fills it in with you. Until it passes, your clips still reach YouTube from the board in two taps.

## TikTok
You need a free TikTok developer app with **Content Posting API** and **Login Kit**. Your Claude runs the `tiktok_token` workflow with you. You then paste three secrets:
- `TT_CLIENT_KEY`
- `TT_CLIENT_SECRET`
- `TT_REFRESH_TOKEN`

Clips land in your TikTok inbox as drafts, which lets you add a trending sound before you tap Post.

## Switch it on
1. Repo → Settings → Secrets and variables → Actions → **Variables** tab → New variable: `AUTOPOST` = `on`
2. Secret `KT_PLATFORMS` = the platforms you connected, for example `instagram,facebook,youtube,tiktok`
3. Secret `KT_SLOTS` = your posting times. Your Claude writes it from what you told it in `start`.
4. Secret `KT_CTA_KEYWORDS` = your comment keyword(s), for example `BRAIN,MONEY`

The machine posts at most every 45 minutes per account, uses one source episode per day at most twice, and never posts the same clip twice.
