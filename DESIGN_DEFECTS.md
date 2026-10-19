# Design defect audit

Audit date: 2026-10-19. This document is the current closeout record for the
rule/runtime/UI lifecycle review. Fixed items have regression coverage where
they can be tested without a live Windows desktop.

## Closed in this pass

- Hook installation failure is reported before the service is marked running.
  The listener creates its message queue before reporting readiness, checks
  message delivery on stop, and releases an installed hook on thread exit.
- Unexpected listener exit is reflected in the GUI instead of leaving a stale
  Stop state. Process/window lookup and callback failures preserve native wheel
  handling.
- Timer shutdown stops accepting frames, clears queued frames, and uses a
  bounded thread join. Scroll queue snapshots and fractional residue handling
  are covered by tests.
- Saving configuration atomically replaces the file and updates the running
  listener's config snapshot without restarting its hook or dropping its
  scroll queue.
- Invalid JSON falls back to built-in config and initialized GUI settings.
  Autostart and language restart now target the script or frozen executable;
  `--tray` starts the service minimized.
- Tray actions are marshalled to the Tk event loop. Single-instance ownership
  uses a Windows named mutex. Exact paths and regex matching are
  case-insensitive, consistent with Windows paths.
- The tray Open menu entry is the default activation action; minimizing the
  window withdraws it only after Tk reports the `iconic` state.
- Main-window geometry is persisted with GUI settings and restored on startup;
  geometry changes are debounced, and tray quit flushes pending settings.
- Exception-list semantics remain: an active entry disables that app; an
  inactive entry restores global fallback; custom entries consume global
  parameters rather than owning separate scroll settings.

## Still open

1. The hidden global fallback can persist `enabled: false`, while the visible
   Start/Stop control describes runtime state. Their relationship is not
   explicit in the UI. Do not add a duplicate generic checkbox; decide whether
   to migrate the legacy flag away or present its state without implying a
   second runtime switch.
2. Configuration schema/numeric bounds are not comprehensively validated.
   Invalid regexes and unreasonable timing/acceleration values need a defined
   reject-or-repair policy before they are accepted into runtime state.
3. Global-rule identity still relies on the regex string `.*`; duplicate or
   equivalent catch-all patterns can be interpreted unexpectedly.
4. Process path lookup still opens/resolves the target process for every wheel
   event. Measure this path on Windows before introducing a cache.

## Acceptance boundary

Automated tests validate rule resolution, config round trips/fallback, timer
and queue behavior, hook failure handling, and UI callback dispatch. They do
not prove native hook behavior on a live Windows desktop. Final acceptance must
exercise continuous scrolling, exception toggles, repeated save while
scrolling, stop/start, tray open/stop/quit, and autostart on Windows. Stop is
bounded, but native API failure can still delay the Tk thread until its timeout.
