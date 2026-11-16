#!/usr/bin/env python3
"""Failure corpus for the gcloud skill. Never reaches Google and never touches the shared config:

* gcloud runs only with CLOUDSDK_CONFIG pointing at an empty throwaway directory, so a command
  either fails in gcloud's parser (bad form) or stops at "no active account" (form is valid).
* the deploy watcher runs against a stub `gcloud` that replays the outcomes seen in sessions.
* the emulator recipe starts a real Firestore emulator on a free port with a demo- project ID.

Throwaway files go under a new /data/tmp/gcloud-skill-test-* directory and are never deleted.
"""
import hashlib, json, os, re, shlex, shutil, signal, socket, subprocess, sys, tempfile, time

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(SKILL_DIR, "scripts", "watch_deploy.py")
BASE = "/data/tmp" if os.path.isdir("/data/tmp") else tempfile.gettempdir()
WORK = tempfile.mkdtemp(prefix="gcloud-skill-test-", dir=BASE)
EMPTY_CFG = os.path.join(WORK, "empty-gcloud-config")
os.makedirs(EMPTY_CFG)
SHARED_CFG = os.path.expanduser("~/.config/gcloud/configurations/config_default")

passed = failed = skipped = 0


def check(ok, label, detail=""):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"\n        {detail}" if (detail and not ok) else ""))


def skip(label):
    global skipped
    skipped += 1
    print(f"  SKIP  {label}")


def fingerprint(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, hashlib.sha256(open(path, "rb").read()).hexdigest())
    except OSError:
        return None


def offline(argv, extra_env=None, cfg=EMPTY_CFG):
    env = dict(os.environ, CLOUDSDK_CONFIG=cfg, CLOUDSDK_CORE_DISABLE_PROMPTS="1")
    for k in ("CLOUDSDK_CORE_PROJECT", "CLOUDSDK_CORE_ACCOUNT", "GOOGLE_APPLICATION_CREDENTIALS"):
        env.pop(k, None)
    env.update(extra_env or {})
    r = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
    return r.returncode, (r.stdout + r.stderr)


AUTH = re.compile(r"do not currently have an active account|does not have any valid credentials")
PARSE = re.compile(r"unrecognized arguments|Invalid choice|ignored explicit argument|must specify a region|argument .+: |is required")


def classify(out):
    if AUTH.search(out):
        return "valid"
    if PARSE.search(out):
        return "parse-error"
    return "other: " + out.strip().splitlines()[0][:120] if out.strip() else "other: (no output)"


shared_before = fingerprint(SHARED_CFG)

# ---------------------------------------------------------------- 1. recorded wrong forms
print("=== 1. forms agents got wrong must fail in the parser; the fixes must parse ===")
P, R = ["--project", "p"], ["--region", "us-central1"]
cases = [
    # (label, argv, expected)
    ("functions list --gen2 (scry, Mar 24)", ["gcloud", "functions", "list", "--gen2"] + P, "parse-error"),
    ("fix: functions list --v2", ["gcloud", "functions", "list", "--v2"] + P, "valid"),
    ("builds log --stream=never (scry, 4x)", ["gcloud", "builds", "log", "--stream=never", "b1"] + R + P, "parse-error"),
    ("fix: builds log <id>", ["gcloud", "builds", "log", "b1"] + R + P, "valid"),
    ("firestore documents list (scry, 3x)", ["gcloud", "firestore", "documents", "list"] + P, "parse-error"),
    ("firestore databases restore --backup (philomena, Nov 10)", ["gcloud", "firestore", "databases", "restore", "--backup=bk1"] + P, "parse-error"),
    ("fix: restore --source-backup --destination-database", ["gcloud", "firestore", "databases", "restore", "--source-backup=projects/p/locations/us/backups/b", "--destination-database=d"] + P, "valid"),
    ("firestore databases clone --source-timestamp (philomena, Nov 10)", ["gcloud", "firestore", "databases", "clone", "--source-timestamp=2026-11-01T00:00:00Z"] + P, "parse-error"),
    ("fix: clone --source-database --snapshot-time", ["gcloud", "firestore", "databases", "clone", "--source-database=projects/p/databases/(default)", "--snapshot-time=2026-11-01T00:00:00Z", "--destination-database=d"] + P, "valid"),
    ("run services describe without --region (philomena, Sep 24)", ["gcloud", "run", "services", "describe", "svc"] + P, "parse-error"),
    ("fix: run services describe --region", ["gcloud", "run", "services", "describe", "svc"] + R + P, "valid"),
    ("HAZARD: builds triggers list without --region parses (so the miss is silent)", ["gcloud", "builds", "triggers", "list"] + P, "valid"),
    ("fix: builds triggers list --region", ["gcloud", "builds", "triggers", "list"] + R + P, "valid"),
    ("beta emulators firestore start --host-port (rusty-seo): not the Firebase CLI path", ["gcloud", "beta", "emulators", "firestore", "start", "--host-port=127.0.0.1:1"], None),
]
for label, argv, want in cases:
    if want is None:
        continue
    rc, out = offline(argv)
    got = classify(out)
    check(got == want, f"{label}: {want}", f"got {got}")

# ---------------------------------------------------------------- 2. every command in SKILL.md parses
print("=== 2. every gcloud command written in SKILL.md parses with gcloud 593 ===")
skill = open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8").read()
code = "\n".join(re.findall(r"```bash\n(.*?)```", skill, re.S)) + "\n" + "\n".join(re.findall(r"`([^`\n]+)`", skill))
subs = [(r'"\$P"', "p"), (r'"\$R"', "us-central1"), (r'"\$A"', "a@b.c"), (r'"\$S"', "svc"),
        (r"\$\(git rev-parse[^)]*\)", "abc1234"), (r"<RFC3339>", "2026-11-01T00:00:00Z"),
        (r"<backup-path>", "projects/p/locations/us/backups/b"), (r"<db-path>", "projects/p/databases/(default)"),
        (r"<[^>]+>", "x")]
def commands_in(text):
    """Yield each `gcloud ...` invocation, ending at an unquoted `|`, newline, or the `)` closing an enclosing $( )."""
    for m in re.finditer(r"(?<![\w-])gcloud ", text):
        i, depth, q, buf = m.start(), 0, None, []
        while i < len(text):
            ch = text[i]
            if q:
                if ch == q:
                    q = None
            elif ch in "'\"":
                q = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in "|\n`":
                break
            buf.append(ch)
            i += 1
        yield "".join(buf)


seen = set()
for raw in commands_in(code):
    cmd = raw.strip().rstrip("\\").strip()
    if "--project" not in cmd or cmd in seen:
        continue
    seen.add(cmd)
    s = cmd
    for a, b in subs:
        s = re.sub(a, b, s)
    try:
        argv = shlex.split(s)
    except ValueError as e:
        check(False, f"SKILL.md command splits: {cmd[:70]}", str(e))
        continue
    got = classify(offline(argv)[1])
    check(got == "valid", f"parses: {cmd[:90]}", f"got {got}")
check(len(seen) >= 15, f"found the skill's commands to test ({len(seen)})")

print("=== 2b. bq flags used in SKILL.md exist (bq checks login before flags, so use its help) ===")
if shutil.which("bq"):
    _, qhelp = offline(["bq", "help", "query"])
    _, ghelp = offline(["bq", "--helpshort"])
    for flag in ["dry_run", "use_legacy_sql", "maximum_bytes_billed"]:
        check(re.search(r"--(\[no\])?" + flag + r"\b", qhelp) is not None, f"bq query --{flag} exists")
    for flag in ["project_id", "location", "format"]:
        check(re.search(r"--" + flag + r"\b", ghelp + qhelp) is not None, f"bq --{flag} exists")
    _, out = offline(["bq", "--project_id=p", "query", "--nouse_legacy_sql", "SELECT 1"], {"CLOUDSDK_CORE_ACCOUNT": "someone@example.com"})
    check("someone@example.com" in out, "bq honours a one-command CLOUDSDK_CORE_ACCOUNT prefix (bq has no --account)", out[:200])
else:
    skip("bq not installed")

# ---------------------------------------------------------------- 3. identity without touching the shared config
print("=== 3. per-command identity works and leaves config files alone ===")
cfg = os.path.join(WORK, "identity-config")
os.makedirs(cfg)
offline(["gcloud", "config", "set", "project", "from-config"], cfg=cfg)
props = os.path.join(cfg, "configurations", "config_default")
before = fingerprint(props)
_, out = offline(["gcloud", "config", "get-value", "project"], {"CLOUDSDK_CORE_PROJECT": "from-env"}, cfg=cfg)
check(out.strip().splitlines()[0] == "from-env", "CLOUDSDK_CORE_PROJECT=... on one command overrides the config's project", out)
check(fingerprint(props) == before, "the env-var form wrote nothing to the config")
_, out = offline(["gcloud", "config", "get-value", "project"], cfg=cfg)
check(out.strip().splitlines()[0] == "from-config", "the next command without it sees the old project again")
_, out = offline(["gcloud", "run", "services", "describe", "svc", "--region", "us-central1", "--project", "p", "--account", "someone@example.com"], cfg=cfg)
check("someone@example.com" in out, "--account selects the account for that command only", out[:200])
offline(["gcloud", "config", "set", "project", "changed-by-agent"], cfg=cfg)
_, out = offline(["gcloud", "config", "get-value", "project"], cfg=cfg)
check(out.strip().splitlines()[0] == "changed-by-agent",
      "HAZARD: `gcloud config set project` persists for every later command using that config (on the shared config: every agent)")

# ---------------------------------------------------------------- 4. the deploy watcher against a stub gcloud
print("=== 4. watch_deploy.py: every deploy outcome seen in sessions ===")
stub_dir = os.path.join(WORK, "stub-bin")
os.makedirs(stub_dir)
STUB = os.path.join(stub_dir, "gcloud")
with open(STUB, "w") as f:
    f.write(r'''#!/usr/bin/env python3
import json, os, sys
sc = json.load(open(os.environ["STUB_SCENARIO"]))
log = os.environ["STUB_LOG"]
with open(log, "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\n")
a = sys.argv[1:]
def out(key):
    v = sc.get(key)
    if isinstance(v, list):
        n_file = os.environ["STUB_LOG"] + "." + key
        n = int(open(n_file).read()) if os.path.exists(n_file) else 0
        open(n_file, "w").write(str(n + 1))
        v = v[min(n, len(v) - 1)]
    if isinstance(v, dict) and "stderr" in v:
        sys.stderr.write(v["stderr"] + "\n"); sys.exit(v.get("rc", 1))
    if not isinstance(v, str):
        v = json.dumps(v)
    sys.stdout.write(v + ("\n" if v else ""))
    sys.exit(0)
if a[:2] == ["builds", "list"]: out("list")
if a[:2] == ["builds", "describe"]:
    out("describe_json" if "json" in a else "status")
if a[:2] == ["builds", "log"]: out("log")
if a[:3] == ["run", "services", "describe"]: out("service")
if a[:3] == ["run", "revisions", "describe"]: out("image")
sys.stderr.write("ERROR: (gcloud) stub: unexpected " + " ".join(a) + "\n"); sys.exit(2)
''')
os.chmod(STUB, 0o755)
SHA = "abc1234def5678"
REAUTH = {"stderr": "ERROR: (gcloud.builds.list) There was a problem refreshing your current auth tokens: Reauthentication failed. cannot prompt during non-interactive execution.", "rc": 1}
DENIED = {"stderr": "ERROR: (gcloud.builds.list) PERMISSION_DENIED: The caller does not have permission. This command is authenticated as deploy@p.iam.gserviceaccount.com", "rc": 1}
FAIL_JSON = {"status": "FAILURE", "failureInfo": {"type": "USER_BUILD_STEP", "detail": "Build step failure: build step 3 \"node:22\" failed"},
             "steps": [{"id": "install", "status": "SUCCESS"}, {"id": "unit-tests", "name": "node:22", "status": "FAILURE"}]}
scenarios = [
    ("live: serving revision carries the commit (philomena prod-<sha> naming)",
     {"list": "b1 QUEUED", "status": ["WORKING", "SUCCESS"], "service": {"status": {"traffic": [{"revisionName": "svc-prod-abc1234-b1", "percent": 100}]}}},
     ["--service", "svc"], 0, ["LIVE"]),
    ("live via image tag when revision names carry no SHA",
     {"list": "b1 WORKING", "status": ["SUCCESS"], "service": {"status": {"traffic": [{"revisionName": "svc-00236-gdk", "percent": 100}]}}, "image": "us-docker.pkg.dev/p/r/img:abc1234"},
     ["--service", "svc"], 0, ["LIVE"]),
    ("green build but an out-of-order older build owns traffic (the Oct 31 rollback)",
     {"list": "b2 QUEUED", "status": ["SUCCESS"], "service": {"status": {"traffic": [{"revisionName": "svc-prod-b4f994b-b0", "percent": 100}]}}, "image": "img:b4f994b"},
     ["--service", "svc"], 3, ["NOT LIVE", "b4f994b"]),
    ("tagged 0% revision does not count as serving",
     {"list": "b1 QUEUED", "status": ["SUCCESS"], "service": {"status": {"traffic": [{"revisionName": "svc-prod-abc1234-b1", "percent": 0, "tag": "new"}, {"revisionName": "svc-prod-0000000-b0", "percent": 100}]}}, "image": "img:0000000"},
     ["--service", "svc"], 3, ["NOT LIVE"]),
    ("build failure: failed step, failureInfo and log tail printed (FAILURE seen 9x, logs never read)",
     {"list": "b3 WORKING", "status": ["WORKING", "FAILURE"], "describe_json": FAIL_JSON, "log": "\n".join(f"line {i}" for i in range(100)) + "\nnpm ERR! test failed"},
     [], 1, ["unit-tests", "USER_BUILD_STEP", "npm ERR! test failed"]),
    ("functions-only project: build SUCCESS is the proof",
     {"list": "b4 QUEUED", "status": ["SUCCESS"]}, [], 0, ["BUILD SUCCESS"]),
    ("no build for the commit (push missing, or trigger in another region)",
     {"list": ""}, ["--find-timeout", "0"], 2, ["NO BUILD", "--region"]),
    ("still running at the cap: bounded, never an endless until-loop",
     {"list": "b5 WORKING", "status": ["WORKING"]}, ["--timeout", "0"], 4, ["still running"]),
    ("expired owner login: stop and ask, no account switching",
     {"list": REAUTH}, [], 5, ["Reauthentication", "ask the owner"]),
    ("deploy SA denied: report, never self-grant",
     {"list": DENIED}, [], 5, ["PERMISSION_DENIED", "do not grant"]),
    ("build log unreadable for this account: failure still reported",
     {"list": "b6 QUEUED", "status": ["FAILURE"], "describe_json": FAIL_JSON, "log": {"stderr": "ERROR: (gcloud.builds.log) PERMISSION_DENIED: Permission denied for all log views", "rc": 1}},
     [], 1, ["unit-tests", "could not read the build log"]),
]
for label, sc, extra, want_rc, want_text in scenarios:
    d = tempfile.mkdtemp(prefix="scenario-", dir=WORK)
    sf, lf = os.path.join(d, "scenario.json"), os.path.join(d, "calls.log")
    json.dump(sc, open(sf, "w"))
    env = dict(os.environ, GCLOUD_BIN=STUB, STUB_SCENARIO=sf, STUB_LOG=lf)
    r = subprocess.run([sys.executable, WATCH, "--project", "p1", "--region", "us-central1", "--account", "deploy@p1.iam.gserviceaccount.com",
                        "--sha", SHA, "--interval", "0"] + extra, capture_output=True, text=True, env=env, timeout=60)
    out = r.stdout + r.stderr
    ok = r.returncode == want_rc and all(t in out for t in want_text)
    check(ok, f"{label}: exit {want_rc}", f"exit {r.returncode}; output: {out[-400:]}")
    calls = [json.loads(l) for l in open(lf)] if os.path.exists(lf) else []
    pinned = calls and all("--project" in c and "p1" in c and "--account" in c and ("--region" in c) for c in calls)
    check(bool(pinned), f"  every gcloud call pinned project, account and region ({len(calls)} calls)")
    check(not any(c[:2] in (["builds", "submit"], ["config", "set"]) or c[:3] == ["run", "services", "update"] for c in calls), "  watcher made no writes")

# ---------------------------------------------------------------- 5. emulator recipe
print("=== 5. emulator recipe: private port, demo- project, bounded wait, stop only our process ===")
fb = shutil.which("firebase")
if not (fb and shutil.which("java")):
    skip("firebase CLI or java missing")
else:
    socks = []
    for _ in range(4):                       # firestore, websocket, hub, logging: all off the defaults
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        socks.append(s)
    port, ws_port, hub_port, log_port = [s.getsockname()[1] for s in socks]
    for s in socks:
        s.close()
    emu = os.path.join(WORK, "emu")
    os.makedirs(emu)
    open(os.path.join(emu, "firestore.rules"), "w").write("rules_version = '2';\nservice cloud.firestore {\n  match /databases/{database}/documents {\n    match /{d=**} { allow read, write: if false; }\n  }\n}\n")
    cfgf = os.path.join(emu, "firebase.json")
    json.dump({"firestore": {"rules": os.path.join(emu, "firestore.rules")},
               "emulators": {"firestore": {"host": "127.0.0.1", "port": port, "websocketPort": ws_port},
                             "hub": {"host": "127.0.0.1", "port": hub_port}, "logging": {"host": "127.0.0.1", "port": log_port},
                             "ui": {"enabled": False}}}, open(cfgf, "w"))
    busy = subprocess.run(["ss", "-ltn"], capture_output=True, text=True).stdout
    check(all(f":{p} " not in busy for p in (port, ws_port, hub_port, log_port)), f"ports {port},{ws_port},{hub_port},{log_port} free before start")
    logf = os.path.join(emu, "emu.log")
    proc = subprocess.Popen([fb, "emulators:start", "--only", "firestore", "--project", "demo-gcloud-skill-test", "--config", cfgf],
                            stdout=open(logf, "w"), stderr=subprocess.STDOUT, cwd=emu, start_new_session=True)
    ready = False
    deadline = time.time() + 120
    while time.time() < deadline and proc.poll() is None:
        text = open(logf).read()
        if "All emulators ready" in text:
            ready = True
            break
        if "Error:" in text:
            break
        time.sleep(1)
    check(ready, "emulator ready within the 120 s cap", open(logf).read()[-500:])
    if ready:
        with socket.socket() as s:
            check(s.connect_ex(("127.0.0.1", port)) == 0, "emulator listening on our private port")
        busy = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True).stdout
        ours = [ln for ln in busy.splitlines() if f"pid={proc.pid}," in ln]
        check(not any(re.search(r":(4400|4500|8080|9150|4000) ", ln) for ln in ours),
              "our emulator holds none of the default ports (4400 hub, 4500 logging, 8080, 9150, 4000)")
    os.killpg(proc.pid, signal.SIGINT)          # our own process group only, never pkill
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=30)
    time.sleep(1)
    with socket.socket() as s:
        check(s.connect_ex(("127.0.0.1", port)) != 0, "port free after stopping our own process")

# ---------------------------------------------------------------- 6. the shared config was never touched
print("=== 6. the shared gcloud config is untouched by this test ===")
check(fingerprint(SHARED_CFG) == shared_before, "~/.config/gcloud/configurations/config_default unchanged")

print(f"\nwork dir (kept): {WORK}")
print(f"{'PASS' if not failed else 'FAIL'}: {passed} pass, {failed} fail, {skipped} skip")
sys.exit(1 if failed else 0)
