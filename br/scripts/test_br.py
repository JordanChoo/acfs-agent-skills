#!/usr/bin/env python3
"""Replay br failure cases from past sessions against the installed br, in throwaway projects.

Each case is a recorded failure (must fail, optionally with a known message) or a step the
skill recommends (must succeed). Every run uses fresh directories under a new temporary root;
nothing is deleted. No project's real .beads is touched.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="br-skill-test-"))
ENV = dict(os.environ, RUST_LOG="error", NO_COLOR="1")
passed = failed = 0


def check(ok, label, detail=""):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))


def run(cwd, *args, actor=None):
    argv = ["br", *args] + (["--actor", actor] if actor else [])
    p = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout + p.stderr


def project(name):
    d = ROOT / name
    d.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True)
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


def main():
    if not shutil.which("br"):
        print("  SKIP  br not on PATH\nPASS: 0 pass, 0 fail, 1 skip")
        return 0
    print(f"=== br skill corpus ({subprocess.run(['br', '--version'], capture_output=True, text=True).stdout.strip()}) ===")
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
    check('"AgentA"' in out, "the first claim survives the second attempt")
    # The hazard behind ~22 logged force-claims: --force rewrites a live claim without warning.
    # Demonstrated on a scratch issue so the skill's "never --force a claim" rule stays grounded.
    victim = create(d, "held by AgentA")
    works("AgentA claims", d, "update", victim, "--claim", actor="AgentA")
    rc, out = run(d, "update", victim, "--status", "in_progress", "--assignee", "AgentB", "--force",
                  actor="AgentB")
    rc2, shown = run(d, "show", victim, "--json")
    check(rc == 0 and '"AgentB"' in shown,
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

    print("--- issues.jsonl conflict recipe ---")
    # Our DB has a local bead; the incoming side's JSONL lacks it. The skill's recipe: put the
    # incoming JSONL in place, import, then flush. The import must MERGE (keep our DB-only bead).
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
    # The recipe (every step allowed by dcg; br needs a .jsonl name, and *.tmp is refused):
    # the incoming version to a sidecar file that is never staged
    # (`git show <ref>:.beads/issues.jsonl > .beads/issues.incoming.jsonl`), import it, then let
    # br regenerate issues.jsonl from the DB, which now holds both sides.
    (conflicted / ".beads" / "issues.incoming.jsonl").write_text(other)
    rc, out = subprocess.run(["br", "sync", "--import-only"], cwd=conflicted, capture_output=True, text=True,
                             env=dict(ENV, BEADS_JSONL=str(conflicted / ".beads" / "issues.incoming.jsonl")),
                             timeout=60).returncode, ""
    check(rc == 0, "works: BEADS_JSONL=.beads/issues.incoming.jsonl br sync --import-only")
    works("br sync --flush-only --force regenerates issues.jsonl from the DB", conflicted,
          "sync", "--flush-only", "--force")
    exported = (conflicted / ".beads" / "issues.jsonl").read_text()
    rc, listed = run(conflicted, "list", "--json")
    check("<<<<<<<" not in exported and "our unpushed bead" in exported and "their bead" in exported
          and "our unpushed bead" in listed and "their bead" in listed,
          "after the recipe: no markers, both sides in the JSONL and the DB")
    # Without markers (for example after a clean merge of two exports), one command is enough.
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
                    ".beads/metadata.json", ".beads/.gitignore"], check=True)
    subprocess.run(["git", "-C", str(main_repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-qm", "beads"], check=True)
    wt = ROOT / "wt-checkout"
    subprocess.run(["git", "-C", str(main_repo), "worktree", "add", "-q", str(wt), "HEAD"], check=True)
    rc, out = run(wt, "show", wid, "--json")
    print(f"  INFO  br show in a fresh worktree before importing: rc={rc}")
    works("import in a fresh worktree", wt, "sync", "--import-only")
    rc, out = run(wt, "show", wid, "--json")
    check(rc == 0 and "tracked issue" in out, "the issue is visible in the worktree after importing")

    print(f"PASS: {passed} pass, {failed} fail, 0 skip")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
