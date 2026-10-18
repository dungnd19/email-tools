# Choosing which emails to download

Open the **Rules & Settings** tab. Your changes are saved automatically when you click Search or close the app. You can also click **Save rules**.

## The settings

| Setting | What it means | Example |
|---|---|---|
| **Subject contains** | The email subject has one of these words. One per line. Upper/lower case doesn't matter. | `invoice`<br>`hóa đơn`<br>`receipt` |
| **From these senders** | The email comes from one of these. One per line. Use a full address, or `@company.com` for anyone at that company. | `billing@abc.com`<br>`@vnpt-invoice.com.vn` |
| **Match** | How the two lists above work together (see below). | Any rule |
| **File types** | Which attachments to save. Emails without these files are not shown. | PDF, E-invoice XML |
| **Other file types** | Anything not in the boxes, separated by commas. | `txt, json` |
| **Save files to** | The folder where files go. | `Documents\Invoices` |

## "Any rule" vs "All rules"

Say the subject words are `invoice` and the senders are `@abc.com`:

| Email | Any rule | All rules |
|---|---|---|
| From abc.com, subject "Invoice #12" | ✅ | ✅ |
| From abc.com, subject "Monthly statement" | ✅ | ❌ |
| From xyz.com, subject "Invoice #99" | ✅ | ❌ |
| From xyz.com, subject "Hello" | ❌ | ❌ |

- **Any rule** finds more emails. Good to start with.
- **All rules** is stricter. Use it if you get too many unrelated emails.
- If you leave one list **empty**, only the other list is used.
- If you leave **both empty**, every email with a matching attachment in the date range is shown.

## File type groups

| Box | Saves |
|---|---|
| PDF | `.pdf` |
| E-invoice XML | `.xml` (Vietnamese hóa đơn điện tử, EU e-invoices) |
| Excel | `.xlsx .xls .xlsm .csv .ods` |
| Word | `.docx .doc .odt .rtf` |
| PowerPoint | `.pptx .ppt .odp` |
| Archives | `.zip .rar .7z` |
| Images | `.jpg .jpeg .png .heic .tif .tiff` (photos/scans of receipts) |

Logos embedded in email signatures are skipped automatically, even when Images is ticked.

## Recipes

**"My supplier always sends from billing@abc.com"**
→ Senders: `billing@abc.com`. Leave Subject empty.

**"Vietnamese e-invoices (hóa đơn điện tử) with PDF + XML"**
→ Subject: `hóa đơn` and `hoá đơn` (both spellings are used) and `invoice`. Tick **PDF** and **E-invoice XML**.

**"Accounting sends statements in Excel"**
→ Subject: `statement` or `sao kê`. Tick **Excel**.

**"Only invoices from 3 vendors, nothing else"**
→ Subject: `invoice`. Senders: the 3 vendors. Match: **All rules**.

**"I get scanned receipts as photos"**
→ Tick **Images**.

## Found nothing?

1. Widen the date range (try **Last month**).
2. Switch Match to **Any rule**.
3. Check the sender spelling. Copy it straight from the email.
4. Make sure the right **file types** are ticked.
5. Try with Subject and Senders empty to see *all* attachments, then narrow it down.
6. Check you signed in with the right Google account (**Sign out of Google** to switch).
