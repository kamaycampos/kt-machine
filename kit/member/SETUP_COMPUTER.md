# Let Claude do the clicking: connect your computer (recommended)

With your permission, your Claude works in **your own Chrome**. It creates your factory, pastes your keys, connects Instagram, Facebook, YouTube and TikTok, and switches on comment → DM. You only **log in** and **approve**. Nothing happens without your OK, and you can watch every click.

Requirements:
- Claude Pro or higher. Claude in Chrome and Remote Control are both included.
- A Mac or PC with Google Chrome

## 1. Add Claude to Chrome (1 min)
1. Open **chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn** → **Add to Chrome**
2. Click the Claude icon in Chrome's toolbar and sign in with your Claude account

## 2. Install Claude on your computer (2 min)
1. Open **Terminal** (Mac: press ⌘ Space, type `Terminal`, press Enter)
2. Paste this line and press Enter:
   ```
   curl -fsSL https://claude.ai/install.sh | bash
   ```
3. Then paste this and press Enter:
   ```
   claude --chrome
   ```
   The first time, a browser window opens. Sign in to Claude and approve.

**If something goes wrong:**
- `command not found: claude`: close Terminal, open a new one, and try `claude --chrome` again. If it still fails, run the install line again.
- "must be logged in": run `claude` on its own once, sign in in the browser it opens, then run `claude --chrome`.

## 3. Say one sentence (the rest is Claude's)
Paste this into Claude and press Enter:

```
Set me up with The Affiliate Factory: make my own copy of github.com/kamaycampos/affiliate-factory, clone it here, read its CLAUDE.md and follow "start".
```

From here, your Claude drives Chrome and stops only when it needs you to **log in** or **approve**:

| Step | Who |
|---|---|
| Create your GitHub account, or log in | **You** log in (Claude fills the form) |
| "Use this template" → your own copy | Claude |
| Your keys into GitHub secrets, and your control panel switched on | Claude |
| Six questions about your voice and audience | **You** answer |
| Instagram → Professional account, linked to your Facebook Page | **You** approve on your phone; Claude does the rest |
| Meta app, permissions, tokens, comment → DM | Claude (**you** click "Continue as…") |
| YouTube: Google Cloud project, API, consent screen, token | Claude (**you** click "Allow") |
| TikTok developer app and token | Claude (**you** log in and approve) |
| A test DM from a second account | Claude tells you what to comment |
| The weekly routine that plans your clips | Claude |

**Want to keep going from your phone?** Type `/remote-control` in the session. You can then follow and continue it in the Claude app while your computer stays on.

If you can't install anything on your computer, setup still works from **claude.ai/code** alone. You then make the clicks yourself, guided one at a time (`SETUP_META.md`, `SETUP_POSTING.md`).
