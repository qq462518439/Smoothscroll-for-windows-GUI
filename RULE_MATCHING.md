# Rule matching contract

The application keeps one internal fallback rule whose regular expression is
`.*`. It is not shown in the application rule list. If a configuration file
does not contain that rule, startup inserts the built-in default. If it exists
with `enabled: false`, that value is preserved and scrolling is disabled for
windows without a matching custom rule.

For a window path, matching is resolved in this order:

1. Matching custom rules are considered in file order; the last matching rule
   wins.
2. A winning custom rule with `exception_active: true` blocks scrolling.
3. A winning custom rule with `exception_active: false` restores the global
   fallback.
4. Only when no custom rule matches is the global rule considered.

The global `enabled` flag controls fallback only. Custom rules do not carry
scroll parameters; they only add or remove a disable exception. Older
configurations that store the custom state in `enabled` are still read, while
new saves use `exception_active` for custom entries.

The acceptance cases are covered by `tests/test_rule_resolution.py`. This
document describes the current stage only; automatic runtime reload remains a
separate later stage.
