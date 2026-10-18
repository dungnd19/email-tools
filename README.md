# Invoice Downloader for Gmail (Windows)

Pick a date range, find your invoice emails in Gmail, and save all their attachments (PDF, XML e-invoices, Excel, Word, and more) into tidy monthly folders on your computer.

No coding or installation needed: it's a single `.exe` file.

![screenshot](docs/img/app.png)

## Quick start

1. **Download** `InvoiceDownloader.exe` from the [Releases page](https://github.com/dungnd19/email-tools/releases/latest).
2. **Connect Google (one time, about 10 minutes)**: follow [docs/SETUP_GOOGLE.md](docs/SETUP_GOOGLE.md). You end up with a file called `credentials.json`.
3. **Use it**: double-click `InvoiceDownloader.exe` → pick **From** and **To** dates → **Search** → **Download selected** → **Open folder**.

The first time you click Search, the app asks for your `credentials.json` and opens your browser so you can sign in to Google. After that it remembers you.

## Where are my files?

```
Documents\Invoices\
  2026-10\
    2026-10-05_vendor.com_INV-1234.pdf
    2026-10-05_vendor.com_INV-1234.xml
  downloaded.csv      ← list of everything downloaded (opens in Excel)
```

- One folder per month. Each file name starts with the email date and the sender's company.
- Emails you've already downloaded show up grey and are not ticked, so you never get duplicates.
- You can change the folder under **Rules & Settings → Save files to**.

## Choosing which emails count as invoices

Open the **Rules & Settings** tab. You can set:
- words the **subject** must contain (e.g. `invoice`, `hóa đơn`)
- **senders** (e.g. `billing@abc.com` or a whole company `@abc.com`)
- which **file types** to save (PDF, XML, Excel, Word, PowerPoint, ZIP, images, or your own)

Examples and tips: [docs/RULES.md](docs/RULES.md).

## Problems?

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Privacy

- The app only asks Google for **read-only** access. It cannot send, delete or change emails.
- Everything stays on your computer. Your sign-in is saved in `%APPDATA%\InvoiceDownloader\`, and **Sign out of Google** in the app deletes it.
- It talks only to Google, using your own Google Cloud project.

## For developers

```bash
pip install -r requirements.txt
python invoice_dl.py            # run the app
python invoice_dl.py --selftest # quick logic checks
```

Pushing a tag such as `v1.0.0` makes GitHub Actions build `InvoiceDownloader.exe` and attach it to a Release.
