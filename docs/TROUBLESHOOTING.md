# Troubleshooting

### "Windows protected your PC"
The app isn't signed with a paid certificate, so Windows warns about it. Click **More info** → **Run anyway**.

### My antivirus deleted or blocked the app
Some antivirus programs distrust apps packed with PyInstaller. Add an exception for `InvoiceDownloader.exe`, or download it again from the official [Releases page](https://github.com/dungnd19/email-tools/releases).

### "Access blocked: Invoice Downloader has not completed the Google verification process" / `access_denied`
Your email isn't on the test-user list. Do [Step 4 of the setup](SETUP_GOOGLE.md#step-4-add-yourself-as-a-test-user-only-if-you-chose-external) and add the exact Gmail address you're signing in with.

### "Google hasn't verified this app"
Normal, because it's your own private app. Click **Continue** (or **Advanced → Go to Invoice Downloader (unsafe)**).

### It asks me to sign in again every week
Your Google project is in **Testing** mode (External audience), and Google ends those sign-ins after 7 days. Just sign in again. If you use Google Workspace, choose **Internal** in Step 3 and this stops.

### "The credentials.json file looks wrong" / `invalid_client`
- In Step 6 you must choose **Desktop app**, not "Web application". Create a new Desktop client and download it again.
- Then: **Rules & Settings → Change credentials.json…**

### The browser says "This site can't be reached" after I click Allow
Close the browser tab and click **Search** in the app again. If it keeps happening, a firewall may be blocking `localhost`. Ask IT to allow it.

### "Cannot reach Google"
Check your internet connection. On a company network, a proxy may be blocking `googleapis.com`.

### Found 0 emails
See ["Found nothing?" in RULES.md](RULES.md#found-nothing).

### An email shows up but a file isn't saved
That file type isn't ticked under **Rules & Settings → File types**. Tick it, or add it to **Other file types**.

### I want to download something again
Rows already downloaded are grey and unticked. Click a row to tick it again. The new copy is saved with `_2` at the end of its name.

### Start completely fresh
Close the app and delete the folder `%APPDATA%\InvoiceDownloader` (paste that into the File Explorer address bar). Your downloaded files are not affected.
