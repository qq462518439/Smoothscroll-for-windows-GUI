# Design defect audit

Audit date: 2026-10-19. This is an inventory of the current design and
runtime defects. No behavior change is implied by this document.

## P0: directly affects whether scrolling works

1. **The global enable state is hidden from the GUI.** The global rule is
   removed from the application list, but the global settings page has no
   enable switch. A saved `enabled: false` therefore looks like a running
   application with no scrolling and cannot be corrected from the UI.
   Evidence: `gui.py:346-400`, `gui.py:424-430`.

2. **Hook installation and callback failures have no recovery path.** The
   code does not check `SetWindowsHookExA` or process/window lookup failures.
   An exception in `get_current_app_path()` or the callback can terminate the
   listener thread while the GUI still reports the service as running.
   Evidence: `smoothscroll/utils/winapi.py:50-68`, `70-83`, `100-107`.

3. **Stopping the service can block or fail.** `join()` posts `WM_QUIT` using
   `native_id` without checking that the thread has started and then waits for
   both listener and timer threads. A failed hook, missing message queue, or
   callback error can leave the GUI stuck during stop/reload.
   Evidence: `smoothscroll/utils/winapi.py:85-93`,
   `smoothscroll/smoothscroll.py:112-114`.

4. **The current automatic reload restarts the service from inside every
   debounced save.** Editing one field can stop and start the hook while the
   user is still changing settings. The stop operation runs synchronously on
   the Tk event thread, so the window can freeze and the active scroll queue
   can be discarded.
   Evidence: `gui.py:612-630`.

5. **Autostart and language restart launch the wrong target.** Autostart
   points at `gui.py --tray`, but `gui.py` does not parse or honor that mode;
   language restart launches `sys.executable` without the application script.
   Evidence: `gui.py:827-835`, `gui.py:548-560`, `gui.py:866-869`.

## P1: rule and configuration model defects

6. **An enabled custom rule can have no scroll configuration.** The GUI adds
   rules with `enabled=True` and `scroll_config=None`. Such a rule matches and
   suppresses the global fallback, so adding an application can disable
   scrolling for that application instead of inheriting or storing a usable
   configuration.
   Evidence: `gui.py:520`, `smoothscroll/utils/winapi.py:33-39`.

7. **Custom rule parameters are not editable.** The UI exposes only the global
   scroll parameters; the application rule editor was replaced by a program
   picker. The data model still permits per-rule parameters, but there is no
   supported way to configure them.
   Evidence: `gui.py:419-535`, `gui.py:346-400`.

8. **Rule identity is encoded by the literal pattern `.*`.** Any user rule
   with that pattern becomes the global rule, duplicate global rules are
   silently collapsed by precedence, and equivalent global expressions such as
   `^.*$` are treated as ordinary custom rules.
   Evidence: `gui.py:428`, `gui.py:700-712`,
   `smoothscroll/utils/winapi.py:23-30`.

9. **Windows path matching is not normalized.** Exact paths are case
   sensitive even though Windows paths are not. Regex flags, slash style, and
   executable naming are left to ad hoc caller behavior.
   Evidence: `smoothscroll/models/scroll.py:44-45`,
   `smoothscroll/utils/winapi.py:24-26`.

10. **Invalid or partial configuration is not validated as a schema.** Bad
    regexes, non-object `scroll_config`, invalid numeric values, zero duration,
    and unsupported key codes can still reach runtime. Some failures happen
    outside the `try` block in `_write_config`.
    Evidence: `gui.py:618-620`, `663-693`, `smoothscroll/models/scroll.py:8-35`.

11. **Configuration writes are not atomic.** A process interruption during the
    direct write can leave a truncated JSON file, after which startup falls
    into the error path.
    Evidence: `gui.py:620-624`.

12. **Malformed configuration can crash startup after showing an error.** On
    load failure, `gui_settings` is not guaranteed to be initialized, but
    `update_gui_from_config()` reads it unconditionally.
    Evidence: `gui.py:575-591`, `gui.py:740-743`.

## P1: scroll execution and concurrency defects

13. **The scroll queue is shared by the hook thread and timer thread without
    synchronization.** The timer iterates a list while removing from it, and
    the hook thread appends concurrently. Events can be skipped, reordered, or
    race with `_pending`.
    Evidence: `smoothscroll/smoothscroll.py:22-24`, `35-47`, `50-89`.

14. **The excess accumulator reset uses the wrong attribute.** The code sets
    `_excess_delta`, but the active state is `_excess_delta_x` and
    `_excess_delta_y`; fractional residue can leak between scroll bursts.
    Evidence: `smoothscroll/smoothscroll.py:25-26`, `72-86`.

15. **Timer failure can deadlock shutdown.** `Timer.run()` has no exception
    boundary around callbacks, and `task_done()` is skipped if a callback
    raises. `Timer.join()` then waits forever on `Queue.join()`.
    Evidence: `smoothscroll/utils/timer.py:11-20`, `34-40`.

16. **Runtime parameters allow mathematically invalid states.** A zero or
    negative duration can divide by zero or schedule invalid animation steps;
    pulse scales and acceleration bounds are not constrained.
    Evidence: `smoothscroll/smoothscroll.py:38-41`, `54-58`,
    `smoothscroll/models/scroll.py:8-35`.

17. **Target-process lookup runs for every wheel event.** Opening the process
    and resolving its module path on every event adds latency and can fail for
    elevated or protected windows. There is no cache or fallback policy.
    Evidence: `smoothscroll/utils/winapi.py:70-75`, `100-107`.

## P2: GUI lifecycle and product consistency defects

18. **Tk widgets are mutated from the tray thread.** `pystray` runs in a
    background thread, but tray callbacks call `toggle_smooth_scroll`,
    `show_window`, and `quit_app`, which directly touch Tk widgets and the root
    window.
    Evidence: `gui.py:790-804`.

19. **The single-instance lock is not atomic and reads `self.lang` before it is
    initialized.** A race can start two instances, and an existing live lock
    can trigger an error path that itself raises `AttributeError`.
    Evidence: `gui.py:239-263`, `gui.py:278`.

20. **The GUI and README describe different products.** README still says
    English/Russian and manual application editing, while the UI includes
    Chinese and the current workflow is a program picker with hidden global
    state.
    Evidence: `README.md`, `gui.py:40-232`, `419-535`.

21. **Windows integration has no end-to-end test coverage.** Existing tests
    only exercise pure rule selection; hook installation, process lookup,
    timer shutdown, GUI save/reload, autostart, and tray lifecycle are
    unverified.

## Fixed in the current working tree, but requiring regression coverage

- Disabled rules retain their scroll parameters.
- Missing global rules are restored during config loading.
- Matching custom rules use last-match precedence and a disabled match blocks
  global fallback.
- Process-name patterns are searched within the full executable path.

## Attack order

1. Restore a visible, explicit global enable control and define its persisted
   semantics.
2. Make hook start/stop and callback failure states observable and bounded.
3. Remove restart-on-every-save; introduce a controlled runtime config update
   only after lifecycle safety is proven.
4. Repair the scroll queue and timer ownership/concurrency.
5. Define and validate the rule/config schema, including custom-rule config.
6. Repair autostart, restart, tray-thread, and single-instance behavior.
7. Add Windows integration tests and update the README to match the product.
