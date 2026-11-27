# vGudia auto-poster: setup guide (free version)

**What it does every hour, fully automatically, with your PC off, for ₹0:**

1. **Reads the news:** the latest Moneycontrol and Inshorts stories.
2. **Writes:** Google **Gemini** (free tier) picks the best stock-market or global-market story. It writes the Bengali poster text, an Instagram caption and a LinkedIn post, and chooses between a **single poster** and a **carousel** (3–6 slides).
3. **Fact check:** a second Gemini check compares every number and name with the source. If something is wrong it rewrites once; if it fails again, nothing is posted.
4. **Makes the poster(s)** in the vGudia design:
   - a matching photo from **Pexels** (free)
   - the **real company logos** (fetched once from Wikipedia and kept in the `logos` folder)
   - typed Bengali text, so it is always spelled correctly
5. **Posts:**
   - **Instagram** gets every post.
   - The **LinkedIn Company Page** gets only the top stories (importance 4–5), at most 4 a day.
6. **Telegram** tells you when something is posted, or when something went wrong.

Everything runs free on **GitHub Actions**.

> 🔒 **Never paste a key or token in a chat, an email or a file.** Keys go only into GitHub's **Secrets** page.

Secrets page: **Settings → Secrets and variables → Actions → New repository secret**

---

## Keys you need

| Secret name | Where to get it | Cost |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com → **Get API key** → Create API key | Free |
| `PEXELS_API_KEY` | pexels.com/api → sign up → **Your API key** | Free |
| `TELEGRAM_BOT_TOKEN` | Telegram **@BotFather** → `/newbot` | Free |
| `TELEGRAM_CHAT_ID` | Send your bot "hi", then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the number after `"chat":{"id":` | Free |
| `IG_ACCESS_TOKEN`, `IG_USER_ID` | See "Instagram" below | Free |
| `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_ORG_ID` | See "LinkedIn" below (add later, once approved) | Free |

Also go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and click Save.

## Instagram

1. In the Instagram app, go to **Settings → Account type and tools → Switch to professional account** and choose **Creator** or **Business**.
2. Go to **developers.facebook.com** and click **My Apps → Create app**. Pick the use case for managing content on Instagram.
3. Open **Instagram → API setup with Instagram login**.
   - Add your account, then click **Generate token**.
   - Allow `instagram_business_basic` and `instagram_business_content_publish`.
4. Copy the **access token** into `IG_ACCESS_TOKEN` and the **Instagram user ID** into `IG_USER_ID`.

> ⏰ The token **expires every 60 days**. When it does, Telegram shows an error. Generate a new token and replace the secret.

## LinkedIn Company Page (start early: approval takes days or weeks)

1. You must be an **admin** of the vGudia Bengali Page.
2. Go to **developer.linkedin.com → Create app**, linked to your Page. On the app's **Settings** tab, **verify** it with the Page.
3. On the **Products** tab, request **Community Management API**. Keep this product on its own app.
4. Once approved, open **Docs and tools → OAuth Token Tools → Create token**. Tick `w_organization_social` and `r_organization_social`, then copy the token into `LINKEDIN_ACCESS_TOKEN`.
5. `LINKEDIN_ORG_ID` is the number in your Page's admin link: `linkedin.com/company/`**`12345678`**`/admin/`

Until LinkedIn is set up, the bot simply posts to Instagram only.

## Test it

1. Open the **Actions** tab, click **Hourly post → Run workflow**.
2. Within about 5 minutes, Telegram should say "✅ Posted" with the Instagram link.
   - "No new stories" or "Skipped" in the log is normal: no suitable story arrived that hour.
3. **Check the first few posts yourself.**

## Logos

- The bot fetches a company's logo **once** and saves it in the `logos` folder (for example `logos/nse.png`).
- **Wrong or old logo?** Replace that file in GitHub (open `logos`, then **Add file → Upload files**, using the same file name).
- **Want your own vGudia logo in the footer?** Upload it as `logo.png` next to `run_hourly.py`. Without it, the footer shows the "vGudia" text.

## Optional settings

Set these under **Settings → Secrets and variables → Actions → Variables tab**.

| Variable | Default | Use |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Change if Google retires this model or a newer free one is out |
| `LINKEDIN_MAX_PER_DAY` | `4` | Maximum LinkedIn posts per day |
| `LINKEDIN_MIN_IMPORTANCE` | `4` | Lower it to `3` to send more stories to LinkedIn |
| `LINKEDIN_VERSION` | `202609` | If LinkedIn says the version is no longer supported, set it to a recent month (YYYYMM) |

## Good to know

- **Free-tier limits:** Gemini's free tier allows plenty for 24 posts a day, but Google can change its free limits. If writing starts failing with "429" errors, that's the free-tier limit.
- **Checks can miss things:** AI checks catch most mistakes, not all. Glance at the page now and then, especially the numbers.
- **Draft cleanup:** draft folders older than 3 days are deleted automatically.
