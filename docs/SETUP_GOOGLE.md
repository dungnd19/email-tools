# Connect Invoice Downloader to your Gmail (one-time setup)

Google requires every app that reads Gmail to be registered. You'll register your own private copy. It's free and takes about 10 minutes. You only do this **once**.

> **Company Google Workspace?** One person (usually IT) can do this once and send the `credentials.json` file to everyone in the company.

You'll need: a computer browser, and the Google account that receives the invoices.

---

## Step 1: Create a project

1. Go to **https://console.cloud.google.com** and sign in.
2. If asked, accept the Terms of Service.
3. At the top left, click **Select a project** (or the current project name) → **New Project**.
4. Project name: `Invoice Downloader` → **Create**.
5. Wait a few seconds, then click **Select project** in the notification.

✅ *You should see "Invoice Downloader" at the top of the page.*

![](img/step-1.png)

## Step 2: Turn on the Gmail API

1. In the search bar at the top, type `Gmail API` and click it.
2. Click the blue **Enable** button.

✅ *You should see a page titled "Gmail API" with "API Enabled".*

![](img/step-2.png)

## Step 3: Set up the sign-in screen

1. In the search bar, type `Google Auth Platform` and open it (older consoles call it **OAuth consent screen**).
2. Click **Get started**.
3. **App name**: `Invoice Downloader`. **User support email**: pick your email → **Next**.
4. **Audience**:
   - **Internal** if your email is a company Google Workspace account (e.g. `you@yourcompany.com`). This is the easiest: no extra steps, and you never have to sign in again.
   - **External** if you use a normal `@gmail.com` account.
   → **Next**
5. **Contact information**: your email → **Next** → tick **I agree** → **Continue** → **Create**.

✅ *You should see "OAuth configuration created".*

![](img/step-3.png)

## Step 4: Add yourself as a test user (only if you chose External)

1. In the left menu click **Audience**.
2. Under **Test users** click **+ Add users**.
3. Type the Gmail address(es) that will use the app → **Save**.

✅ *Your email is listed under Test users.*

> ℹ️ In this "Testing" mode Google asks you to **sign in again every 7 days**. The app opens the browser automatically when that happens. Just click Allow. Up to 100 people can be test users.

![](img/step-4.png)

## Step 5: Allow read-only Gmail access

1. In the left menu click **Data Access** → **Add or remove scopes**.
2. In the filter box type `gmail.readonly`.
3. Tick the row `.../auth/gmail.readonly` ("View your email messages and settings") → **Update** → **Save**.

✅ *`gmail.readonly` is listed under "Your restricted scopes".*

> This only lets the app **read** emails. It can't send, delete or change anything.

![](img/step-5.png)

## Step 6: Download your credentials file

1. In the left menu click **Clients** → **+ Create client**.
2. **Application type**: **Desktop app** (important: not "Web application").
3. Name: `Invoice Downloader` → **Create**.
4. In the popup click **Download JSON**. (Missed it? Click the client name, then the download icon.)
5. Find the downloaded file (it has a long name like `client_secret_1234…json`) and **rename it to `credentials.json`**.
6. Move it somewhere safe, e.g. `Documents`.

✅ *You have a file called `credentials.json`.*

> 🔒 Don't post this file publicly. It's fine to share it with coworkers who will use the app.

![](img/step-6.png)

## Step 7: Connect the app

1. Double-click **InvoiceDownloader.exe**.
   - If Windows says *"Windows protected your PC"*, click **More info** → **Run anyway**. (The app isn't signed with a paid certificate.)
2. Click **🔍 Search**. The app asks for your credentials file → choose `credentials.json`.
3. Your browser opens. Choose your Google account.
4. You'll see **"Google hasn't verified this app"**. That's expected: it's *your own* app, which you just created. Click **Continue** (or **Advanced → Go to Invoice Downloader (unsafe)**).
5. Tick the permission box if one is shown → **Continue**.
6. The browser says *"The authentication flow has completed"*. Close the tab and go back to the app.

✅ *The app shows "Found N emails". Setup is done! 🎉*

![](img/step-7.png)

---

### Switching to another Google account
**Rules & Settings → Sign out of Google**, then Search again and pick the other account.

### Got a new credentials file?
**Rules & Settings → Change credentials.json…**

Stuck? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
