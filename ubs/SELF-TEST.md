# UBS skill verification

Run from the canonical skill repo:

```bash
bash scripts/test-all.sh --skill ubs
# To see every individual test and retained artifact path:
bash ubs/scripts/self-test.sh
```

The runner uses Python's standard-library `unittest`, temporary fixture Git
repositories and a fake UBS executable to replay failure envelopes, then invokes
the installed UBS on tiny JS and Rust fixtures. It never installs/updates tools,
uses a paid endpoint, modifies the caller's Git index, or deletes its fixtures.
A missing installed UBS fails the live-test setup; it is not counted as a pass.
Test directories are printed and retained for inspection.

## Cases exercised

| Regression case | Test / expected behavior |
|---|---|
| Empty output parsed as zero findings | `test_empty_output_is_not_zero_findings`: incomplete, exit 2 |
| Exit lost through a parser or `|| true` | `test_stderr_and_real_exit_are_retained`, `test_parser_cannot_erase_nonzero_or_hidden_critical` |
| Partial/crashed/refused/legacy-unknown scan | Fifteen envelope subcases in `test_replay_empty_partial_legacy_and_malformed_outputs` |
| Exit 0 with 613 warnings called clean | `test_zero_exit_with_warnings_is_review_required` |
| Unsupported Markdown called clean | `test_live_unsupported_markdown_is_not_a_pass`: exit 3 |
| Mixed supported/unsupported files | `test_mixed_scope_keeps_manual_review_requirement` |
| Empty staged scope falling into a full scan | `test_empty_staged_scope_never_runs_bare_ubs`: no scanner process |
| Untracked files omitted / spaces or newlines split / leading dash read as flag | `test_exact_filenames_and_untracked_scope` |
| Staged and working-tree contents differ | `test_partially_staged_files_are_refused` |
| Concurrent edits invalidate evidence | `test_changing_source_invalidates_scan` |
| Post-scan input read fails after a successful scanner exit | `test_post_scan_io_failure_cannot_keep_a_success_status` |
| Scope escaping repo / output-mode overrides | `test_external_paths_and_report_overrides_are_refused` |
| Broad ignores hide a real bug | `test_live_ignore_keeps_a_real_finding`: generated artifact excluded, source canary retained |
| Rust assertions overwhelm production findings | `test_live_rust_test_filter_retains_production_findings`: supplemental filter removes test assertion, retains production unwrap |
| Original self-test exits on its first successful counter increment under `set -e` | `test_old_shell_counter_does_not_test_successfully_under_errexit` reproduces old failure and verifies the corrected increment |
| Format/locations and critical failure still work | `test_live_clean_dirty_and_locations` |

The suite verifies capture/scope/classification and current CLI behavior. It does
not prove agents will follow prose or that UBS finds every real bug. The manual
replay review in `references/SESSION-FINDINGS.md` checks instructions for failures
such as weakening correct code, blanket test exclusions, premature closeout, and
outdated flag claims. No model adherence percentage is claimed.
