# vGudia auto-poster: setup guide

**What it does every hour, fully automatically, with your PC off:**

1. **Reads the news:** the latest Moneycontrol and Inshorts stories.
2. **Writes:** Claude picks the best stock-market or global-market story. It writes the Bengali poster text, an Instagram caption and a LinkedIn post. It also decides between a **single poster** (quick news) and a **carousel** (big stories, 3–6 slides).
3. **Fact check:** a second Claude check compares every number and name with the source story. If anything is wrong, it rewrites once. If it fails again, nothing is posted.
4. **Draws:** OpenAI's image model draws the poster(s) in the vGudia style.
5. **Poster check:** Claude reads each poster and checks the Bengali text is exact, with no invented numbers and no logos. If not, it redraws, up to 3 tries.
6. **Posts:**
   - **Instagram** gets every post that passes.
   - The **LinkedIn Company Page** gets only the most important stories (importance 4–5 out of 5), at most 4 a day.
7. **Tells you on Telegram:** each "✅ Posted" with links, plus anything that was held back.
   - A single poster that fails its poster check comes with **Approve / Reject / New image** buttons. You don't have to answer: after 6 hours it expires and nothing is posted.

Everything runs free on **GitHub Actions**. You only pay for the Claude API and the OpenAI API.

> 🔒 **Never paste a key or token in a chat, an email or a file.** Keys go only into GitHub's **Secrets** page (step 7).

---

## Step 1: Put the code on GitHub

1. Create a free account at github.com.
2. Click **+ → New repository**. Name it `vgudia-bot` and choose **Public**.
   - Public is required: Instagram downloads the posters from the repository's public link. Your keys stay private in Secrets.
3. On the new repository page, click **uploading an existing file**.
4. Drag in everything in this folder **except** `posts` and `sample_prompt.txt`: `src`, `.github`, the three `run_….py` files, `requirements.txt`, `.gitignore`, `SETUP.md`. Then click **Commit changes**.
5. Check that the repository shows `.github/workflows` with `hourly.yml` and `approvals.yml` inside.
   - If it's missing, create each file with **Add file → Create new file**: type the name `.github/workflows/hourly.yml` and paste in that file's contents. Do the same for `approvals.yml`.

## Step 2: Create the Telegram bot (for notifications)

1. In Telegram, open **@BotFather**, send `/newbot`, and choose a name and a username ending in `bot`.
2. BotFather replies with a **token**. Keep it for step 7.
3. Open your new bot and send it `hi`.
4. In a browser, open this link with your token in place of `<TOKEN>`:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   Find `"chat":{"id":123456789`. That number is your **chat ID**.

## Step 3: Get the Claude API key (writing and checks)

1. Go to **console.anthropic.com**, sign up and add credit under **Billing**.
2. Under **API keys**, create a key.

## Step 4: Get the OpenAI API key (draws the posters)

This is separate from ChatGPT Go and billed per image.

1. Go to **platform.openai.com**, sign up and add credit under **Billing**.
2. Under **API keys**, create a key.
3. OpenAI may ask you to **verify your organization** (Settings → Organization) before its image models work. Do this if asked.

## Step 5: Connect Instagram

1. In the Instagram app, go to **Settings → Account type and tools → Switch to professional account** and choose **Creator** or **Business**.
2. Go to **developers.facebook.com** and click **My Apps → Create app**. Pick the use case for managing content on Instagram.
3. Open **Instagram → API setup with Instagram login**.
   - Add your Instagram account, then click **Generate token**.
   - Allow `instagram_business_basic` and `instagram_business_content_publish`.
4. Copy the **access token** and your **Instagram user ID**.

> ⏰ The Instagram token **expires every 60 days**. When it does, posting stops and Telegram shows the error. Generate a new token on the same page and replace `IG_ACCESS_TOKEN` (step 7).

## Step 6: Connect the LinkedIn Company Page (start early: approval takes time)

LinkedIn only lets apps post to Company Pages after it approves the app for the **Community Management API**. This can take days or weeks. Instagram works without it in the meantime.

1. You must be an **admin of the vGudia Bengali Company Page**.
2. Go to **developer.linkedin.com → Create app**. Link it to your Company Page and upload a logo. Then, on the app's **Settings** tab, **verify** the app with your Page.
3. On the **Products** tab, request **Community Management API**. Fill in the form: you are a company posting your own content to your own Page.
   - LinkedIn wants this product on an app of its own, so don't add other products to this app.
4. Once approved, open **Docs and tools → OAuth Token Tools → Create token**. Tick `w_organization_social` and `r_organization_social`, sign in, and copy the **access token**.
5. Your **organization ID** is the number in your Page's admin link: `linkedin.com/company/`**`12345678`**`/admin/`

> ⏰ LinkedIn tokens also expire, usually after 60 days. Renew the token the same way when Telegram shows a LinkedIn error.

## Step 7: Add the keys to GitHub Secrets

In your repository, go to **Settings → Secrets and variables → Actions → New repository secret**. Add each one:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Claude key (step 3) |
| `OPENAI_API_KEY` | OpenAI key (step 4) |
| `TELEGRAM_BOT_TOKEN` | Bot token (step 2) |
| `TELEGRAM_CHAT_ID` | Your chat ID number (step 2) |
| `IG_ACCESS_TOKEN` | Instagram token (step 5) |
| `IG_USER_ID` | Instagram user ID (step 5) |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn token (step 6; add it later once approved) |
| `LINKEDIN_ORG_ID` | Company Page number (step 6) |

Also go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and click Save.

## Step 8: Test it

1. Open the **Actions** tab. If asked, click **I understand, enable workflows**.
2. Click **Hourly post → Run workflow**.
   - Within about 3–10 minutes, Telegram should say "✅ Posted" with the Instagram link.
   - "No new stories" or "Skipped" in the log is normal: no suitable story arrived that hour.
3. **Check the first few posts on Instagram yourself.** If something is off, tell me what, and I'll tighten the rules.

From then on, it runs every hour by itself.

---

## Optional settings

Set these under **Settings → Secrets and variables → Actions → Variables tab**.

| Variable | Default | Use |
|---|---|---|
| `CLAUDE_MODEL` | `claude-opus-5-5` | Set to `claude-sonnet-5-5` to make the writing and checks cost about half |
| `OPENAI_IMAGE_MODEL` | `gpt-image-1` | Set to OpenAI's newest image model name if a newer one is out |
| `OPENAI_IMAGE_QUALITY` | `high` | `medium` is cheaper, but Bengali text fails the check more often |
| `LINKEDIN_MAX_PER_DAY` | `4` | Maximum LinkedIn posts per day |
| `LINKEDIN_MIN_IMPORTANCE` | `4` | Lower it to `3` to send more stories to LinkedIn |
| `PENDING_HOURS` | `6` | How long a held-back draft waits for your tap before it expires |
| `LINKEDIN_VERSION` | `202609` | LinkedIn API month. If LinkedIn says the version is no longer supported, set it to a recent month (YYYYMM) |

## Approximate running cost (24 posts a day)

- **Claude (writing, fact check, poster check):** roughly $0.10–0.20 per post on Opus 5.5, or about half on Sonnet 5.5.
- **OpenAI images:** one image per single post, 3–6 per carousel, plus any redraws. Check the current price at platform.openai.com/pricing. This is usually the biggest cost.
- **GitHub, Telegram, Instagram and LinkedIn APIs:** free.

**Set a monthly spending limit on both the Anthropic and OpenAI billing pages.**

## Good to know

- **The checks catch most mistakes, not all:** AI checks can miss a mistake. Look through the page now and then, especially the numbers.
- **Draft cleanup:** draft folders older than 3 days are deleted automatically.
- **If the news sites change their pages,** the log will show "No new stories" for many hours in a row. That means the news reader needs updating.
