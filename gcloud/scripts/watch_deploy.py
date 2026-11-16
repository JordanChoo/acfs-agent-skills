#!/usr/bin/env python3
"""Watch the Cloud Build run for one pushed commit and, optionally, prove a Cloud Run service serves it.

Replaces hand-written `until gcloud builds list ...; do sleep; done` loops. Read-only: it only runs
`gcloud builds list|describe|log` and `gcloud run services|revisions describe`.

  watch_deploy.py --project P --region R --sha <commit> [--account A] [--service S]
                  [--find-timeout 600] [--timeout 1800] [--interval 20]

Exit codes:
  0  build SUCCESS (and, with --service, a serving revision carries the commit)
  1  build finished FAILURE / INTERNAL_ERROR / TIMEOUT / CANCELLED / EXPIRED (failure details printed)
  2  no build for this commit appeared within --find-timeout (push missing? wrong region or project?)
  3  build SUCCESS but the service does not serve this commit (another build owns traffic)
  4  build still running at --timeout
  5  gcloud failed (auth expired, permission denied, bad flag); its ERROR line is printed
"""
import argparse, json, os, re, subprocess, sys, time

TERMINAL_BAD = {"FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED"}


class GcloudError(Exception):
    pass


def gcloud(args, opts):
    argv = [os.environ.get("GCLOUD_BIN", "gcloud")] + args + ["--project", opts.project]
    if opts.account:
        argv += ["--account", opts.account]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    err = r.stderr.strip()
    if r.returncode != 0 or re.search(r"^ERROR: \(", err, re.M):
        line = next((l for l in err.splitlines() if l.startswith("ERROR")), err[:300] or f"exit {r.returncode}")
        raise GcloudError(line)
    return r.stdout


def advice(msg):
    if re.search(r"Reauthentication|refreshing your current auth|does not have any valid credentials|active account", msg):
        return "Login expired or missing. Stop and ask the owner to run `gcloud auth login --no-launch-browser` in their own terminal; do not switch accounts."
    if "PERMISSION_DENIED" in msg or "does not have permission" in msg:
        return "This account lacks the permission. Check --account and --project; do not grant yourself roles or switch to the owner account without asking."
    if "unrecognized arguments" in msg or "Invalid choice" in msg:
        return "Bad flag. Check `gcloud <group> <command> --help`."
    return ""


def find_build(opts, short):
    deadline = time.time() + opts.find_timeout
    while True:
        out = gcloud(["builds", "list", "--region", opts.region, "--limit", "1",
                      "--filter", f"substitutions.SHORT_SHA={short}",
                      "--format", "value(id,status)"], opts).strip()
        if out:
            bid, status = (out.split() + [""])[:2]
            return bid, status
        if time.time() >= deadline:
            return None, None
        time.sleep(opts.interval)


def wait_build(opts, bid):
    deadline = time.time() + opts.timeout
    last = None
    while True:
        status = gcloud(["builds", "describe", bid, "--region", opts.region, "--format", "value(status)"], opts).strip()
        if status != last:
            print(f"build {bid}: {status}", flush=True)
            last = status
        if status == "SUCCESS" or status in TERMINAL_BAD:
            return status
        if time.time() >= deadline:
            return "STILL_RUNNING"
        time.sleep(opts.interval)


def report_failure(opts, bid):
    info = gcloud(["builds", "describe", bid, "--region", opts.region, "--format", "json"], opts)
    try:
        b = json.loads(info)
    except ValueError:
        b = {}
    fi = b.get("failureInfo") or {}
    print(f"failureInfo: {fi.get('type', '')} {fi.get('detail', '')}".rstrip())
    if b.get("statusDetail"):
        print(f"statusDetail: {b['statusDetail']}")
    for s in b.get("steps") or []:
        if s.get("status") in TERMINAL_BAD:
            print(f"failed step: id={s.get('id', '?')} name={s.get('name', '?')} status={s.get('status')}")
    try:
        log = gcloud(["builds", "log", bid, "--region", opts.region], opts)
        print("--- last 60 log lines ---")
        print("\n".join(log.splitlines()[-60:]))
    except GcloudError as e:
        print(f"(could not read the build log: {e}; {advice(str(e))})")


def serving(opts, short):
    svc = json.loads(gcloud(["run", "services", "describe", opts.service, "--region", opts.region, "--format", "json"], opts))
    traffic = [t for t in (svc.get("status") or {}).get("traffic") or [] if t.get("percent", 0) > 0]
    for t in traffic:
        rev = t.get("revisionName", "")
        if short in rev:
            return True, rev
        image = gcloud(["run", "revisions", "describe", rev, "--region", opts.region,
                        "--format", "value(spec.containers[0].image)"], opts).strip()
        if short in image:
            return True, rev
    return False, ", ".join(f"{t.get('revisionName')}={t.get('percent')}%" for t in traffic) or "no revision with traffic"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--sha", required=True, help="pushed commit (full or short)")
    ap.add_argument("--account")
    ap.add_argument("--service", help="Cloud Run service that must end up serving the commit")
    ap.add_argument("--find-timeout", type=int, default=600)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--interval", type=int, default=20)
    opts = ap.parse_args()
    short = opts.sha[:7]
    try:
        bid, status = find_build(opts, short)
        if not bid:
            print(f"NO BUILD for {short} in {opts.project}/{opts.region} after {opts.find_timeout}s. "
                  f"Check the push reached the remote, and that the trigger is in this region "
                  f"(`gcloud builds triggers list --region {opts.region} --project {opts.project}`).")
            return 2
        print(f"build {bid} for {short}: {status}", flush=True)
        status = wait_build(opts, bid)
        if status == "STILL_RUNNING":
            print(f"build {bid} still running after {opts.timeout}s; rerun to keep watching.")
            return 4
        if status != "SUCCESS":
            report_failure(opts, bid)
            return 1
        if opts.service:
            ok, what = serving(opts, short)
            if not ok:
                print(f"BUILD SUCCESS BUT NOT LIVE: {opts.service} serves {what}, not {short}. "
                      f"A green build is not proof: a newer (or out-of-order older) build may own traffic.")
                return 3
            print(f"LIVE: {opts.service} serves {what} ({short}).")
        else:
            print(f"BUILD SUCCESS for {short}.")
        return 0
    except GcloudError as e:
        print(f"GCLOUD ERROR: {e}\n{advice(str(e))}".rstrip())
        return 5


if __name__ == "__main__":
    sys.exit(main())
