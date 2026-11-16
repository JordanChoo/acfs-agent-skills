#!/usr/bin/env python3
"""Replay br failure cases from past sessions against the installed br, in throwaway projects.

Cases check real refusals, supported steps and explicitly labeled legacy hazards.
Every run uses fresh directories under a retained temporary root with isolated routing;
nothing is deleted. No project's real .beads is touched. Presence of two distinct issue
titles in a legacy union fixture does not prove preservation of arbitrary conflicting data.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="br-skill-test-"))
# Inherited routing overrides must never send these scratch operations to a real DB.
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("BEADS_", "BR_", "BD_", "GIT_"))}
ENV.update(RUST_LOG="error", NO_COLOR="1", XDG_CONFIG_HOME=str(ROOT / "config"))
ENV.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
passed = failed = 0


def check(ok, label, detail=""):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))


def run(cwd, *args, actor=None):
    cwd = Path(cwd).resolve()
    if not cwd.is_relative_to(ROOT.resolve()):
        raise ValueError("refusing a fixture outside the retained test root")
    argv = ["br", "--db", str(cwd / ".beads/beads.db"), *args] + (["--actor", actor] if actor else [])
    p = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=60, check=False)
    return p.returncode, p.stdout + p.stderr


def project(name):
    d = ROOT / name
    d.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True, env=ENV, timeout=30)
    rc, out = run(d, "init", "--prefix", "t")
    assert rc == 0, out
    return d


def create(d, title, *extra):
    rc, out = run(d, "create", "--title", title, "-t", "task", "-p", "2", "--json", *extra)
    assert rc == 0, out
    return json.loads(out[out.index("{"):out.rindex("}") + 1])["id"]


def fails(label, d, *args, contains=None, actor=None):
    rc, out = run(d, *args, actor=actor)
    ok = rc != 0 and (contains is None or contains.lower() in out.lower())
    check(ok, f"fails: {label}", f"rc={rc} out={out.strip()[:160]}")


def works(label, d, *args, actor=None):
    rc, out = run(d, *args, actor=actor)
    check(rc == 0, f"works: {label}", f"rc={rc} out={out.strip()[:160]}")
    return out


def issue(d, issue_id):
    rc, out = run(d, "show", issue_id, "--json")
    assert rc == 0, out
    rows = json.loads(out)
    assert isinstance(rows, list) and len(rows) == 1 and rows[0]["id"] == issue_id
    return rows[0]


def recovery_regressions():
    print("--- Preservation and optimistic concurrency regressions ---")
    check(not any(k.startswith(("BEADS_", "BR_", "BD_")) for k in ENV),
          "routing overrides are removed from fixture environment")
    try:
        run(ROOT.parent, "where", "--json")
    except ValueError:
        check(True, "fixture runner refuses paths outside retained root")
    else:
        check(False, "fixture runner refuses paths outside retained root")
    d = project("preservation")
    a = create(d, "original issue", "--description", "Original reviewed description with enough detail")
    b = create(d, "separate prerequisite")
    works("append first note", d, "update", a, "--append-notes", "first evidence")
    works("append second note", d, "update", a, "--append-notes", "second evidence")
    check(issue(d, a)["notes"] == "first evidence\nsecond evidence", "append preserves earlier evidence")
    old = issue(d, a)["updated_at"]
    works("peer revision", d, "update", a, "--append-notes", "peer evidence")
    fails("stale if-unchanged update", d, "update", a, "--title", "stale replacement", "--if-unchanged", old)
    check(issue(d, a)["title"] == "original issue" and "peer evidence" in issue(d, a)["notes"],
          "optimistic mismatch preserves peer revision")
    works("reviewed current update", d, "update", a, "--title", "reviewed issue",
          "--if-unchanged", issue(d, a)["updated_at"])
    fails("short destructive description rewrite", d, "update", a, "--description", "x")
    check(issue(d, a)["description"].startswith("Original reviewed"), "rewrite refusal preserves description")
    works("relation to prerequisite", d, "dep", "add", a, b)
    works("preservation comment", d, "comments", "add", a, "retain this comment")
    works("preservation flush", d, "sync", "--flush-only")
    family = {p.name: p.read_bytes() for p in (d / ".beads").iterdir()
              if p.is_file() and (p.name.startswith("beads.db") or p.name.endswith(".jsonl"))}
    rc, out = run(d, "sync", "--reconcile-additive", "--json")
    check(rc == 0, "additive reconciliation plan succeeds without apply")
    plan = json.loads(out)
    check(bool(plan.get("plan_sha256")), "plan carries a review-bound digest")
    after = {p.name: p.read_bytes() for p in (d / ".beads").iterdir()
             if p.is_file() and (p.name.startswith("beads.db") or p.name.endswith(".jsonl"))}
    check(family == after, "plan leaves DB family, JSONL and base byte-identical")
    works("change after reviewed plan", d, "update", b, "--append-notes", "new evidence")
    fails("stale reconciliation plan token", d, "sync", "--reconcile-additive", "--apply",
          "--expect-plan-sha256", plan["plan_sha256"], "--json")
    rows = {r["id"]: r for r in map(json.loads, (d / ".beads/issues.jsonl").read_text().splitlines())}
    check({a, b}.issubset(rows)
          and any(dep["issue_id"] == a and dep["depends_on_id"] == b and dep["type"] == "blocks"
                  for dep in rows[a].get("dependencies", []))
          and any(comment["issue_id"] == a and comment["text"] == "retain this comment"
                  for comment in rows[a].get("comments", []))
          and rows[a]["notes"] == "first evidence\nsecond evidence\npeer evidence",
          "export preserves exact IDs, comment text, dependency direction and notes")
    clash = project("same-id-conflict")
    shared = create(clash, "shared original")
    works("shared base flush", clash, "sync", "--flush-only")
    source_path = clash / ".beads/issues.jsonl"
    source_rows = list(map(json.loads, source_path.read_text().splitlines()))
    works("local edit without export", clash, "update", shared, "--title", "local intended title", "--no-auto-flush")
    local = issue(clash, shared)
    for row in source_rows:
        if row["id"] == shared:
            row["title"] = "incoming competing title"
            row["updated_at"] = local["updated_at"]
    source_path.write_text("".join(json.dumps(row) + "\n" for row in source_rows))
    fails("same-ID equal-timestamp semantic conflict", clash, "sync", "--merge")
    check("incoming competing title" in source_path.read_text(), "merge refusal preserves incoming evidence")


def main():
    if not shutil.which("br"):
        print("FAIL: br not on PATH; live corpus NOT RUN")
        return 1
    print(f"=== br skill corpus ({subprocess.run(['br', '--version'], capture_output=True, text=True, timeout=15, check=False).stdout.strip()}) ===")
    print(f"  (fixtures retained under {ROOT})")

    print("--- Commands from outdated AGENTS.md files ---")
    d = project("stale-docs")
    a = create(d, "first")
    fails("br prime (philomena, big-flare AGENTS.md)", d, "prime")
    fails("br import -i (scry AGENTS.md)", d, "import", "-i", ".beads/issues.jsonl")
    # Older br rejected `doctor --fix`; 0.7.6 accepts it as an alias of --repair, which REBUILDS
    # the DB from JSONL. The skill teaches the read-only check and a dry run first.
    works("br doctor --repair --dry-run (plans only)", d, "doctor", "--repair", "--dry-run")
    fails("br update --add-note", d, "update", a, "--add-note", "x")
    fails("br update --blocks", d, "update", a, "--blocks", a)
    fails("br list --parent", d, "list", "--parent", a)
    works("br sync --import-only (instead of br import)", d, "sync", "--import-only")
    works("br doctor (read-only check)", d, "doctor")
    works("br update --append-notes (instead of --add-note)", d, "update", a, "--append-notes", "progress note")
    works("br comments add", d, "comments", "add", a, "a comment")

    print("--- Values and statuses ---")
    fails("priority as a word", d, "create", "--title", "x", "-p", "high")
    works("priority as P1", d, "create", "--title", "p-word", "-t", "task", "-p", "P1", "--json")
    fails("update --status closed (must use br close)", d, "update", a, "--status", "closed")
    desc = d / "desc.md"
    desc.write_text("- [ ] starts with a dash\n- [ ] second item\n")
    works("create --description-file with markdown", d, "create", "--title", "with file", "-t", "task",
          "-p", "2", "--description-file", str(desc), "--json")
    works("acceptance text starting with '- '", d, "update", a, "--acceptance-criteria", "- [ ] item")
    works("comments add -f file", d, "comments", "add", a, "-f", str(desc))
    works("--lock-timeout as two words", d, "--lock-timeout", "30000", "list", "--json")

    print("--- Claiming ---")
    blocker = create(d, "blocker")
    blocked = create(d, "blocked")
    works("dep add blocked -> blocker", d, "dep", "add", blocked, blocker)
    fails("claim a blocked issue", d, "update", blocked, "--claim", actor="AgentA")
    works("claim an unblocked issue", d, "update", blocker, "--claim", actor="AgentA")
    fails("second agent claims a held issue", d, "update", blocker, "--claim", actor="AgentB")
    rc, out = run(d, "show", blocker, "--json")
    check(issue(d, blocker).get("assignee") == "AgentA", "the first claim survives the second attempt")
    # The hazard behind ~22 logged force-claims: --force rewrites a live claim without warning.
    # Demonstrated on a scratch issue so the skill's "never --force a claim" rule stays grounded.
    victim = create(d, "held by AgentA")
    works("AgentA claims", d, "update", victim, "--claim", actor="AgentA")
    rc, out = run(d, "update", victim, "--status", "in_progress", "--assignee", "AgentB", "--force",
                  actor="AgentB")
    rc2, shown = run(d, "show", victim, "--json")
    check(rc == 0 and issue(d, victim).get("assignee") == "AgentB",
          "HAZARD confirmed: --force silently replaces another agent's live claim", f"rc={rc}")
    works("return a claim (status open, no assignee)", d, "update", blocker, "--status", "open",
          "--assignee", "", actor="AgentA")
    fails("dependency cycle", d, "dep", "add", blocker, blocked)
    works("dep cycles is empty", d, "dep", "cycles")

    print("--- Closing ---")
    works("close with an evidence reason", d, "close", blocker, "--reason",
          "Completed. commit=abc1234; tests: crate::tests::x passed")
    works("blocked issue is ready after its blocker closes", d, "ready", "--json")
    works("epic close-eligible --dry-run lists without closing", d, "epic", "close-eligible", "--dry-run")

    print("--- Database and JSONL after a pull ---")
    upstream = project("upstream")
    create(upstream, "made by another agent")
    works("upstream flush", upstream, "sync", "--flush-only")
    local = project("local")
    create(local, "local work")
    works("local flush", local, "sync", "--flush-only")
    # Simulate `git pull` bringing another agent's issue into issues.jsonl.
    pulled = (upstream / ".beads" / "issues.jsonl").read_text()
    jsonl = local / ".beads" / "issues.jsonl"
    jsonl.write_text(jsonl.read_text() + pulled)
    fails("flush over a JSONL that has issues the DB lacks", local, "sync", "--flush-only",
          contains="refus")
    works("import after the pull", local, "sync", "--import-only")
    works("flush after importing", local, "sync", "--flush-only")
    rc, out = run(local, "list", "--json")
    check("made by another agent" in out and "local work" in out, "both issues present after import")
    works("sync --status", local, "sync", "--status")
    works("doctor --robot-triage (read-only JSON)", local, "doctor", "--robot-triage")
    rc, out = run(local, "sync", "--help")
    check("--merge" in out, "sync --merge exists for JSONL conflicts")

    print("--- Legacy distinct-ID conflict hazard demonstration (not a recovery recipe) ---")
    # Historical fixture: presence of two distinct titles does not prove lossless semantics.
    theirs = project("conflict-theirs")
    create(theirs, "their bead")
    works("their flush", theirs, "sync", "--flush-only")
    ours = project("conflict-ours")
    create(ours, "our unpushed bead")
    works("our flush", ours, "sync", "--flush-only")
    (ours / ".beads" / "issues.jsonl").write_text((theirs / ".beads" / "issues.jsonl").read_text())
    # Trap found while testing: import merges into the DB, but a plain flush then exports
    # nothing ("no dirty issues"), so the JSONL would silently drop our bead.
    trap = project("conflict-trap")
    create(trap, "our unpushed bead")
    run(trap, "sync", "--flush-only")
    (trap / ".beads" / "issues.jsonl").write_text((theirs / ".beads" / "issues.jsonl").read_text())
    run(trap, "sync", "--import-only")
    run(trap, "sync", "--flush-only")
    check("our unpushed bead" not in (trap / ".beads" / "issues.jsonl").read_text(),
          "TRAP confirmed: import then plain flush leaves our bead out of the JSONL")
    # A real conflict leaves markers in issues.jsonl; br refuses to touch it.
    conflicted = project("conflict-markers")
    create(conflicted, "our unpushed bead")
    run(conflicted, "sync", "--flush-only")
    mine = (conflicted / ".beads" / "issues.jsonl").read_text()
    other = (theirs / ".beads" / "issues.jsonl").read_text()
    (conflicted / ".beads" / "issues.jsonl").write_text(
        f"<<<<<<< HEAD\n{mine}=======\n{other}>>>>>>> incoming\n")
    fails("flush while issues.jsonl has conflict markers", conflicted, "sync", "--flush-only",
          contains="conflict markers")
    fails("merge while issues.jsonl has conflict markers", conflicted, "sync", "--merge",
          contains="conflict markers")
    # Legacy forced export on a scratch fixture only; never a permission precedent:
    # the incoming version to a sidecar file that is never staged
    # (`git show <ref>:.beads/issues.jsonl > .beads/issues.incoming.jsonl`), import it, then let
    # br regenerates the distinct-ID fixture; no claim about arbitrary semantic conflicts.
    (conflicted / ".beads" / "issues.incoming.jsonl").write_text(other)
    imported = subprocess.run(["br", "--db", str(conflicted / ".beads/beads.db"), "sync", "--import-only"],
                              cwd=conflicted, capture_output=True, text=True,
                              env=dict(ENV, BEADS_JSONL=str(conflicted / ".beads/issues.incoming.jsonl")),
                              timeout=60, check=False)
    check(imported.returncode == 0, "legacy fixture only: sidecar import",
          (imported.stdout + imported.stderr).strip()[:160])
    works("legacy fixture only: forced export of known distinct IDs", conflicted,
          "sync", "--flush-only", "--force")
    exported = (conflicted / ".beads" / "issues.jsonl").read_text()
    rc, listed = run(conflicted, "list", "--json")
    check("<<<<<<<" not in exported and "our unpushed bead" in exported and "their bead" in exported
          and "our unpushed bead" in listed and "their bead" in listed,
          "legacy distinct-ID fixture has both titles (not proof of safe recovery)")
    # Narrow historical marker-free fixture; success is not general semantic preservation.
    works("br sync --merge on a marker-free incoming issues.jsonl", ours, "sync", "--merge")
    exported = (ours / ".beads" / "issues.jsonl").read_text()
    check("our unpushed bead" in exported and "their bead" in exported,
          "br sync --merge keeps both sides")
    rc, out = run(ours, "sync", "--help")
    check("removes DB entries not in JSONL" in out.replace("remove DB entries", "removes DB entries")
          or "remove DB entries not in JSONL" in out,
          "help confirms --import-only --rebuild deletes DB-only entries (guarded in SKILL.md)")

    print("--- Worktrees ---")
    main_repo = project("wt-main")
    wid = create(main_repo, "tracked issue")
    works("flush before commit", main_repo, "sync", "--flush-only")
    subprocess.run(["git", "-C", str(main_repo), "add", ".beads/issues.jsonl", ".beads/config.yaml",
                    ".beads/metadata.json", ".beads/.gitignore"], check=True, env=ENV, timeout=30)
    subprocess.run(["git", "-C", str(main_repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-qm", "beads"], check=True, env=ENV, timeout=30)
    wt = ROOT / "wt-checkout"
    subprocess.run(["git", "-C", str(main_repo), "worktree", "add", "-q", str(wt), "HEAD"],
                   check=True, env=ENV, timeout=30)
    rc, out = run(wt, "show", wid, "--json")
    print(f"  INFO  br show in a fresh worktree before importing: rc={rc}")
    works("import in a fresh worktree", wt, "sync", "--import-only")
    rc, out = run(wt, "show", wid, "--json")
    check(rc == 0 and "tracked issue" in out, "the issue is visible in the worktree after importing")

    recovery_regressions()
    print(f"PASS: {passed} pass, {failed} fail, 0 skip")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
