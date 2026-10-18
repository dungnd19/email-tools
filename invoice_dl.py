"""Invoice Downloader: pick dates, find invoice emails in Gmail, save their attachments."""
import base64
import csv
import datetime as dt
import json
import os
import re
import shutil
import sys
import threading
from email.utils import parseaddr
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "InvoiceDownloader"
CRED_FILE = APP_DIR / "credentials.json"
TOKEN_FILE = APP_DIR / "token.json"
SETTINGS_FILE = APP_DIR / "settings.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
INDEX_NAME = "downloaded.csv"

FILE_GROUPS = {
    "PDF": ["pdf"],
    "E-invoice XML": ["xml"],
    "Excel": ["xlsx", "xls", "xlsm", "csv", "ods"],
    "Word": ["docx", "doc", "odt", "rtf"],
    "PowerPoint": ["pptx", "ppt", "odp"],
    "Archives (zip, rar)": ["zip", "rar", "7z"],
    "Images": ["jpg", "jpeg", "png", "heic", "tif", "tiff"],
}


def documents_dir():
    # Documents is often redirected to OneDrive, so ~/Documents can be the wrong folder.
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        return Path(os.path.expandvars(winreg.QueryValueEx(key, "Personal")[0]))
    except Exception:
        return Path.home() / "Documents"


DEFAULTS = {
    "keywords": ["invoice", "hóa đơn", "receipt"],
    "senders": [],
    "match": "any",
    "groups": ["PDF", "E-invoice XML", "Excel", "Word"],
    "other_ext": "",
    "save_root": str(documents_dir() / "Invoices"),
}


def load_settings():
    try:
        return {**DEFAULTS, **json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))}
    except Exception:
        return dict(DEFAULTS)


def save_settings(s):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- pure logic (covered by --selftest) ----------

def extensions(s):
    exts = {e for g in s["groups"] for e in FILE_GROUPS.get(g, [])}
    exts |= {e.strip(". ").lower() for e in re.split(r"[,\s]+", s["other_ext"]) if e.strip(". ")}
    return exts


def ext_allowed(name, exts):
    return Path(name).suffix.lower().lstrip(".") in exts


def build_query(s, d_from, d_to):
    # Epoch seconds = local midnight; Gmail reads plain YYYY/MM/DD as Pacific time.
    start = int(dt.datetime.combine(d_from, dt.time()).timestamp())
    end = int(dt.datetime.combine(d_to + dt.timedelta(days=1), dt.time()).timestamp())  # before: is exclusive
    q = [f"after:{start}", f"before:{end}", "has:attachment"]
    kws = [f'subject:"{k.replace(chr(34), "")}"' for k in s["keywords"] if k.strip()]
    frm = [f"from:{x.strip().lstrip('@')}" for x in s["senders"] if x.strip()]
    parts = ["(" + " OR ".join(p) + ")" for p in (kws, frm) if p]
    if len(parts) == 2:
        q.append(f"({parts[0]} OR {parts[1]})" if s["match"] == "any" else f"{parts[0]} {parts[1]}")
    elif parts:
        q.append(parts[0])
    exts = sorted(extensions(s))
    if exts:
        q.append("(" + " OR ".join(f"filename:{e}" for e in exts) + ")")
    return " ".join(q)


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name[:150] or "file"


def unique_path(p):
    n, out = 2, p
    while out.exists():
        out = p.with_name(f"{p.stem}_{n}{p.suffix}")
        n += 1
    return out


# ---------- Gmail ----------

def gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES) if TOKEN_FILE.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:  # e.g. invalid_grant after 7 days in Google "Testing" mode
            creds = None
    if not creds or not creds.valid:
        creds = InstalledAppFlow.from_client_secrets_file(str(CRED_FILE), SCOPES).run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def find_attachments(payload, exts):
    stack, out = [payload], []
    while stack:
        p = stack.pop()
        stack += p.get("parts", [])
        name = p.get("filename")
        if not name or not ext_allowed(name, exts):
            continue
        disp = next((h["value"] for h in p.get("headers", []) if h["name"].lower() == "content-disposition"), "")
        if disp.lower().startswith("inline") and ext_allowed(name, FILE_GROUPS["Images"]):
            continue  # signature logos etc.
        out.append((name, p.get("body", {})))
    return out


def search(service, query, exts, progress):
    ids, token = [], None
    while True:
        r = service.users().messages().list(userId="me", q=query, pageToken=token, maxResults=500).execute()
        ids += [m["id"] for m in r.get("messages", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    mails = []
    # ponytail: one request per email, fine for hundreds; switch to batch requests if people search thousands.
    for i, mid in enumerate(ids, 1):
        progress(f"Reading email {i} of {len(ids)}…")
        m = service.users().messages().get(userId="me", id=mid, format="full").execute()
        files = find_attachments(m["payload"], exts)
        if not files:
            continue
        h = {x["name"].lower(): x["value"] for x in m["payload"].get("headers", [])}
        addr = parseaddr(h.get("from", ""))
        mails.append({
            "id": mid,
            "date": dt.datetime.fromtimestamp(int(m["internalDate"]) / 1000).date(),
            "sender": addr[0] or addr[1],
            "domain": addr[1].split("@")[-1] or "unknown",
            "subject": h.get("subject", "(no subject)"),
            "files": files,
        })
    return sorted(mails, key=lambda m: m["date"])


def read_index(root):
    try:
        with open(root / INDEX_NAME, encoding="utf-8-sig", newline="") as f:
            return {row["gmail_id"] for row in csv.DictReader(f)}
    except FileNotFoundError:
        return set()


def download(service, mail, root):
    folder = root / mail["date"].strftime("%Y-%m")
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for name, body in mail["files"]:
        data = body.get("data")
        if not data and body.get("attachmentId"):
            data = service.users().messages().attachments().get(
                userId="me", messageId=mail["id"], id=body["attachmentId"]).execute()["data"]
        if not data:
            continue
        path = unique_path(folder / safe_filename(f"{mail['date']}_{mail['domain']}_{name}"))
        path.write_bytes(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
        saved.append(path)
    index = root / INDEX_NAME
    new = not index.exists()
    with open(index, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "sender", "subject", "file", "gmail_id"])
        for p in saved:
            w.writerow([mail["date"], mail["sender"], mail["subject"], str(p.relative_to(root)), mail["id"]])
    return len(saved)


def friendly(e):
    text = str(e)
    if "access_denied" in text:
        return "Google refused the sign-in.\nIf your app is in Testing mode, add your Gmail as a Test user (see docs/SETUP_GOOGLE.md)."
    if isinstance(e, OSError) or "Unable to find the server" in text or "timed out" in text:
        return "Cannot reach Google. Check your internet connection and try again."
    if "invalid_client" in text or "client_secret" in text:
        return "The credentials.json file looks wrong.\nDownload it again (Desktop app type) and choose it under Settings → Change credentials."
    return f"Something went wrong:\n\n{text}"


# ---------- UI ----------

def run_app():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkcalendar import DateEntry

    s = load_settings()
    root = tk.Tk()
    root.title("Invoice Downloader")
    root.geometry("900x560")
    state = {"mails": {}, "checked": set(), "service": None}

    def ui(fn, *a):
        root.after(0, lambda: fn(*a))

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=8, pady=8)
    tab_dl, tab_rules = ttk.Frame(nb, padding=8), ttk.Frame(nb, padding=8)
    nb.add(tab_dl, text="  Download  ")
    nb.add(tab_rules, text="  Rules & Settings  ")

    # --- Rules tab ---
    def labeled_text(row, label, lines, hint):
        ttk.Label(tab_rules, text=label, font=("", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=4)
        t = tk.Text(tab_rules, height=4, width=40, font=("", 10))
        t.insert("1.0", "\n".join(lines))
        t.grid(row=row, column=1, sticky="we", pady=4)
        ttk.Label(tab_rules, text=hint, foreground="gray").grid(row=row, column=2, sticky="nw", padx=8)
        return t

    kw_box = labeled_text(0, "Subject contains", s["keywords"], "One word or phrase per line.\nExample: invoice")
    from_box = labeled_text(1, "From these senders", s["senders"],
                            "One per line. A full address\n(billing@abc.com) or a whole\ncompany (@abc.com).")
    match = tk.StringVar(value=s["match"])
    mf = ttk.Frame(tab_rules)
    ttk.Label(tab_rules, text="Match", font=("", 10, "bold")).grid(row=2, column=0, sticky="w", pady=4)
    ttk.Radiobutton(mf, text="Any rule (subject OR sender)", variable=match, value="any").pack(side="left")
    ttk.Radiobutton(mf, text="All rules (subject AND sender)", variable=match, value="all").pack(side="left", padx=12)
    mf.grid(row=2, column=1, columnspan=2, sticky="w")

    ttk.Label(tab_rules, text="File types", font=("", 10, "bold")).grid(row=3, column=0, sticky="nw", pady=4)
    gf = ttk.Frame(tab_rules)
    group_vars = {}
    for i, g in enumerate(FILE_GROUPS):
        group_vars[g] = tk.BooleanVar(value=g in s["groups"])
        ttk.Checkbutton(gf, text=g, variable=group_vars[g]).grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 14))
    gf.grid(row=3, column=1, columnspan=2, sticky="w")
    ttk.Label(tab_rules, text="Other file types", font=("", 10, "bold")).grid(row=4, column=0, sticky="w", pady=4)
    other = tk.StringVar(value=s["other_ext"])
    ttk.Entry(tab_rules, textvariable=other).grid(row=4, column=1, sticky="we")
    ttk.Label(tab_rules, text="Example: txt, json", foreground="gray").grid(row=4, column=2, sticky="w", padx=8)

    ttk.Label(tab_rules, text="Save files to", font=("", 10, "bold")).grid(row=5, column=0, sticky="w", pady=4)
    save_root = tk.StringVar(value=s["save_root"])
    ttk.Entry(tab_rules, textvariable=save_root).grid(row=5, column=1, sticky="we")
    ttk.Button(tab_rules, text="Browse…",
               command=lambda: save_root.set(filedialog.askdirectory(initialdir=save_root.get()) or save_root.get())
               ).grid(row=5, column=2, sticky="w", padx=8)
    tab_rules.columnconfigure(1, weight=1)

    def current_settings():
        lines = lambda t: [x.strip() for x in t.get("1.0", "end").splitlines() if x.strip()]
        return {"keywords": lines(kw_box), "senders": lines(from_box), "match": match.get(),
                "groups": [g for g, v in group_vars.items() if v.get()], "other_ext": other.get(),
                "save_root": save_root.get()}

    def pick_credentials():
        f = filedialog.askopenfilename(title="Choose your credentials.json",
                                       filetypes=[("Google credentials", "*.json")])
        if not f:
            return False
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, CRED_FILE)
        TOKEN_FILE.unlink(missing_ok=True)
        state["service"] = None
        messagebox.showinfo("Invoice Downloader", "Credentials saved. Click Search to sign in.")
        return True

    def sign_out():
        TOKEN_FILE.unlink(missing_ok=True)
        state["service"] = None
        messagebox.showinfo("Invoice Downloader", "Signed out. You will sign in again on the next search.")

    af = ttk.Frame(tab_rules)
    ttk.Button(af, text="Save rules", command=lambda: (save_settings(current_settings()),
                                                       messagebox.showinfo("Invoice Downloader", "Rules saved."))
               ).pack(side="left")
    ttk.Button(af, text="Change credentials.json…", command=pick_credentials).pack(side="left", padx=8)
    ttk.Button(af, text="Sign out of Google", command=sign_out).pack(side="left")
    af.grid(row=6, column=0, columnspan=3, sticky="w", pady=16)

    # --- Download tab ---
    top = ttk.Frame(tab_dl)
    top.pack(fill="x")
    today = dt.date.today()
    ttk.Label(top, text="From").pack(side="left")
    d_from = DateEntry(top, date_pattern="yyyy-mm-dd", width=12)
    d_from.set_date(today.replace(day=1))
    d_from.pack(side="left", padx=4)
    ttk.Label(top, text="To").pack(side="left", padx=(8, 0))
    d_to = DateEntry(top, date_pattern="yyyy-mm-dd", width=12)
    d_to.pack(side="left", padx=4)

    def set_range(first, last):
        d_from.set_date(first)
        d_to.set_date(last)

    def last_month():
        end = today.replace(day=1) - dt.timedelta(days=1)
        set_range(end.replace(day=1), end)

    ttk.Button(top, text="This month", command=lambda: set_range(today.replace(day=1), today)).pack(side="left", padx=4)
    ttk.Button(top, text="Last month", command=last_month).pack(side="left")
    search_btn = ttk.Button(top, text="🔍 Search")
    search_btn.pack(side="left", padx=12)

    cols = ("pick", "date", "from", "subject", "files")
    tree = ttk.Treeview(tab_dl, columns=cols, show="headings", selectmode="none")
    for c, title, w in zip(cols, ("✔", "Date", "From", "Subject", "Files"), (40, 90, 180, 330, 220)):
        tree.heading(c, text=title)
        tree.column(c, width=w, stretch=c in ("subject", "files"), anchor="center" if c == "pick" else "w")
    tree.tag_configure("done", foreground="gray")
    sb = ttk.Scrollbar(tab_dl, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="top", fill="both", expand=True, pady=8)

    def set_checked(iid, on):
        (state["checked"].add if on else state["checked"].discard)(iid)
        tree.set(iid, "pick", "☑" if on else "☐")

    def toggle(e):
        iid = tree.identify_row(e.y)
        if iid:
            set_checked(iid, iid not in state["checked"])

    tree.bind("<Button-1>", toggle)

    bottom = ttk.Frame(tab_dl)
    bottom.pack(fill="x")
    ttk.Button(bottom, text="Select all", command=lambda: [set_checked(i, True) for i in tree.get_children()]
               ).pack(side="left")
    ttk.Button(bottom, text="Select none", command=lambda: [set_checked(i, False) for i in tree.get_children()]
               ).pack(side="left", padx=4)
    dl_btn = ttk.Button(bottom, text="⬇ Download selected")
    dl_btn.pack(side="left", padx=12)

    def open_folder():
        p = Path(save_root.get())
        p.mkdir(parents=True, exist_ok=True)
        os.startfile(p)

    ttk.Button(bottom, text="📂 Open folder", command=open_folder).pack(side="left")
    bar = ttk.Progressbar(bottom, length=160)
    bar.pack(side="right")
    status = ttk.Label(tab_dl, text="Pick dates and click Search.")
    status.pack(fill="x", pady=(6, 0))

    def busy(on):
        for b in (search_btn, dl_btn):
            b.state(["disabled"] if on else ["!disabled"])

    def worker(job):
        def run():
            try:
                if state["service"] is None:
                    ui(status.config, text="Waiting for Google sign-in in your browser…")
                    state["service"] = gmail_service()
                job(state["service"])
            except Exception as e:
                ui(messagebox.showerror, "Invoice Downloader", friendly(e))
                ui(status.config, text="Stopped.")
            finally:
                ui(busy, False)
        busy(True)
        threading.Thread(target=run, daemon=True).start()

    def show_results(mails, done_ids):
        tree.delete(*tree.get_children())
        state["mails"], state["checked"] = {}, set()
        for m in mails:
            done = m["id"] in done_ids
            tree.insert("", "end", iid=m["id"], tags=("done",) if done else (),
                        values=("☐", m["date"], m["sender"], m["subject"] + ("  (already downloaded)" if done else ""),
                                ", ".join(n for n, _ in m["files"])))
            state["mails"][m["id"]] = m
            set_checked(m["id"], not done)
        new = len(mails) - sum(m["id"] in done_ids for m in mails)
        status.config(text=f"Found {len(mails)} emails ({new} new). Tick the ones you want and click Download.")

    def on_search():
        if not CRED_FILE.exists():
            messagebox.showinfo("Invoice Downloader",
                                "First time? Choose the credentials.json file you made with the setup guide "
                                "(docs/SETUP_GOOGLE.md).")
            if not pick_credentials():
                return
        cur = current_settings()
        if not extensions(cur):
            return messagebox.showwarning("Invoice Downloader", "Tick at least one file type under Rules & Settings.")
        if d_from.get_date() > d_to.get_date():
            return messagebox.showwarning("Invoice Downloader", "The From date is after the To date.")
        save_settings(cur)
        query, exts, root_dir = build_query(cur, d_from.get_date(), d_to.get_date()), extensions(cur), Path(cur["save_root"])

        def job(svc):
            mails = search(svc, query, exts, lambda t: ui(status.config, text=t))
            ui(show_results, mails, read_index(root_dir))
        status.config(text="Searching…")
        worker(job)

    def on_download():
        picked = [state["mails"][i] for i in tree.get_children() if i in state["checked"]]
        if not picked:
            return messagebox.showinfo("Invoice Downloader", "Nothing ticked. Click a row to tick it.")
        root_dir = Path(save_root.get())

        def job(svc):
            total = 0
            ui(bar.config, maximum=len(picked), value=0)
            for i, m in enumerate(picked, 1):
                total += download(svc, m, root_dir)
                ui(bar.config, value=i)
                ui(status.config, text=f"Downloading {i} of {len(picked)} emails…")
            ui(status.config, text=f"Done. Saved {total} files to {root_dir}")
            ui(lambda: [tree.item(m["id"], tags=("done",)) or set_checked(m["id"], False) for m in picked])
        worker(job)

    search_btn.config(command=on_search)
    dl_btn.config(command=on_download)
    root.protocol("WM_DELETE_WINDOW", lambda: (save_settings(current_settings()), root.destroy()))
    root.mainloop()


def selftest():
    s = {**DEFAULTS, "keywords": ["invoice", 'hóa "đơn'], "senders": ["@abc.com", "x@y.com"],
         "groups": ["PDF", "Word"], "other_ext": ".TXT, json"}
    d = dt.date(2026, 10, 1)
    q = build_query(s, d, d)
    start = int(dt.datetime(2026, 10, 1).timestamp())
    assert q.startswith(f"after:{start} before:{start + 86400} has:attachment"), q
    assert '((subject:"invoice" OR subject:"hóa đơn") OR (from:abc.com OR from:x@y.com))' in q, q
    assert "filename:docx" in q and "filename:txt" in q and "filename:json" in q, q
    q_all = build_query({**s, "match": "all"}, d, d)
    assert '(subject:"invoice" OR subject:"hóa đơn") (from:abc.com OR from:x@y.com)' in q_all, q_all
    assert "from:" not in build_query({**s, "senders": []}, d, d)
    exts = extensions(s)
    assert ext_allowed("report.docx", exts) and ext_allowed("INV.PDF", exts) and ext_allowed("a.txt", exts)
    assert not ext_allowed("logo.png", exts) and not ext_allowed("doc_scan.xlsx", exts)
    assert safe_filename('a<b>:c"/d\\e|f?g*.pdf') == "a_b__c__d_e_f_g_.pdf"
    assert safe_filename(" .. ") == "file"
    payload = {"parts": [
        {"filename": "INV-1.pdf", "body": {"attachmentId": "A"}, "headers": []},
        {"filename": "logo.png", "body": {"data": "x"},
         "headers": [{"name": "Content-Disposition", "value": "inline"}]},
        {"parts": [{"filename": "list.docx", "body": {"data": "eA"}, "headers": []}]},
    ]}
    assert sorted(n for n, _ in find_attachments(payload, exts | {"png"})) == ["INV-1.pdf", "list.docx"]
    print("selftest ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else run_app()
