// Copyright Motia LLC and/or licensed to Motia LLC under one or more
// contributor license agreements. Licensed under the Elastic License 2.0;
// you may not use this file except in compliance with the Elastic License 2.0.
// This software is patent protected. We welcome discussions - reach out at team@iii.dev
// See LICENSE and PATENTS files for details.

//! `iii worker catalog` — curated, categorized discovery of the first-party
//! workers that ship with iii.
//!
//! The rest of the worker CLI assumes you already know a worker's name:
//! `add`, `reinstall`, `update`, `sync` all take a name and install it. There
//! was no way to answer "what can I install, and how?" from the CLI itself.
//!
//! This command fills that gap the way an "awesome list" does for a language
//! ecosystem: a grouped index of installable capabilities, each paired with
//! the exact `iii worker add` command. It is intentionally offline and local —
//! it lists the workers baked into this engine build, so it works with no
//! network and never drifts from the binary you are running. Browse the full
//! community registry at <https://workers.iii.dev>.

use colored::Colorize;
use std::io::Write;

/// One installable first-party worker.
pub struct CatalogEntry {
    /// Registry name passed to `iii worker add` (e.g. `iii-queue`).
    pub name: &'static str,
    /// Grouping shown as a section header. See [`CATEGORY_ORDER`].
    pub category: &'static str,
    /// One-line description, sourced from the worker's README.
    pub summary: &'static str,
}

/// Section order for grouped output. Categories are printed in this order;
/// any category not listed here sorts last, alphabetically.
pub const CATEGORY_ORDER: &[&str] = &[
    "Networking",
    "Messaging",
    "State & Data",
    "Scheduling",
    "Execution",
    "Federation",
    "Observability",
    "Configuration",
    "Runtime",
];

/// The curated catalog. Summaries are condensed from each worker's
/// `engine/src/workers/*/README.md`. The `catalog_covers_builtins` test keeps
/// this in lockstep with [`crate::cli::builtin_defaults`] so a newly shipped
/// builtin can't silently go undocumented here.
pub const CATALOG: &[CatalogEntry] = &[
    CatalogEntry {
        name: "iii-http",
        category: "Networking",
        summary: "Expose registered functions as HTTP endpoints.",
    },
    CatalogEntry {
        name: "iii-queue",
        category: "Messaging",
        summary: "Asynchronous job queues with retries and dead-letter support.",
    },
    CatalogEntry {
        name: "iii-pubsub",
        category: "Messaging",
        summary: "Topic-based publish/subscribe for real-time event broadcast.",
    },
    CatalogEntry {
        name: "iii-stream",
        category: "State & Data",
        summary: "Durable real-time data streams clients subscribe to over WebSocket.",
    },
    CatalogEntry {
        name: "iii-state",
        category: "State & Data",
        summary: "Distributed key-value state with reactive change triggers.",
    },
    CatalogEntry {
        name: "iii-cron",
        category: "Scheduling",
        summary: "Run functions on a schedule using cron expressions.",
    },
    CatalogEntry {
        name: "iii-sandbox",
        category: "Execution",
        summary: "Ephemeral libkrun micro-VMs for running untrusted code.",
    },
    CatalogEntry {
        name: "iii-exec",
        category: "Execution",
        summary: "Run shell commands at engine startup — builds, migrations, daemons.",
    },
    CatalogEntry {
        name: "iii-bridge",
        category: "Federation",
        summary: "Bridge this engine to another iii instance to share functions.",
    },
    CatalogEntry {
        name: "iii-observability",
        category: "Observability",
        summary: "OpenTelemetry tracing, logs, metrics, and alert rules.",
    },
    CatalogEntry {
        name: "configuration",
        category: "Configuration",
        summary: "Schema-validated, reactive registry of named configuration entries.",
    },
    CatalogEntry {
        name: "iii-worker-manager",
        category: "Runtime",
        summary: "Mandatory listener that SDK workers connect to (default port 49134).",
    },
];

/// Case-insensitive substring match against a worker's name, category, and
/// summary. An empty/whitespace-only query matches everything.
pub fn entry_matches(entry: &CatalogEntry, query: &str) -> bool {
    let q = query.trim().to_lowercase();
    if q.is_empty() {
        return true;
    }
    entry.name.to_lowercase().contains(&q)
        || entry.category.to_lowercase().contains(&q)
        || entry.summary.to_lowercase().contains(&q)
}

/// Sort key for a category: its index in [`CATEGORY_ORDER`], or `len` (last)
/// when unlisted. Ties broken alphabetically by the caller.
fn category_rank(category: &str) -> usize {
    CATEGORY_ORDER
        .iter()
        .position(|c| *c == category)
        .unwrap_or(CATEGORY_ORDER.len())
}

/// Return the matching entries grouped into `(category, entries)` sections in
/// display order. Entries within a section preserve their order in [`CATALOG`].
pub fn grouped_matches(query: &str) -> Vec<(&'static str, Vec<&'static CatalogEntry>)> {
    let mut categories: Vec<&'static str> = Vec::new();
    for entry in CATALOG {
        if entry_matches(entry, query) && !categories.contains(&entry.category) {
            categories.push(entry.category);
        }
    }
    categories.sort_by(|a, b| category_rank(a).cmp(&category_rank(b)).then(a.cmp(b)));

    categories
        .into_iter()
        .map(|category| {
            let entries: Vec<&'static CatalogEntry> = CATALOG
                .iter()
                .filter(|e| e.category == category && entry_matches(e, query))
                .collect();
            (category, entries)
        })
        .collect()
}

/// Render and print the catalog. `query` filters case-insensitively;
/// `names_only` prints just the matching worker names (one per line) for
/// scripting. Returns a process exit code: `0` on any match, `1` when a query
/// matched nothing.
pub fn run(query: Option<&str>, names_only: bool) -> i32 {
    let query = query.unwrap_or("");
    let groups = grouped_matches(query);

    let stdout = std::io::stdout();
    let mut out = stdout.lock();

    if groups.is_empty() {
        // Diagnostics go to stderr so `--names-only` stdout stays clean.
        eprintln!(
            "No workers match '{}'. Run `iii worker catalog` to see them all,",
            query.trim()
        );
        eprintln!("or browse the full registry at https://workers.iii.dev");
        return 1;
    }

    if names_only {
        for (_, entries) in &groups {
            for entry in entries {
                let _ = writeln!(out, "{}", entry.name);
            }
        }
        return 0;
    }

    let _ = writeln!(out);
    let _ = writeln!(
        out,
        "  {}",
        "First-party iii workers — install with `iii worker add <name>`".bold()
    );

    for (category, entries) in &groups {
        let _ = writeln!(out);
        let _ = writeln!(out, "  {}", category.bold().underline());
        for entry in entries {
            // Pad the plain name to a fixed column FIRST, then colorize. Width
            // specifiers count bytes, so `{:22}` applied to a ColoredString
            // would pad against the invisible ANSI escape codes and misalign
            // the summary column whenever stdout is a TTY.
            let name_col = format!("{:22}", entry.name);
            let _ = writeln!(out, "    {} {}", name_col.cyan(), entry.summary.dimmed());
        }
    }

    let _ = writeln!(out);
    let _ = writeln!(
        out,
        "  {}",
        "Browse the full community registry at https://workers.iii.dev".dimmed()
    );
    let _ = writeln!(out);
    0
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cli::builtin_defaults::{BUILTIN_NAMES, OPTIONAL_BUILTIN_NAMES};
    use std::collections::HashSet;

    fn catalog_names() -> HashSet<&'static str> {
        CATALOG.iter().map(|e| e.name).collect()
    }

    /// The catalog must list every user-installable builtin. If someone adds a
    /// new builtin worker, this fails until they document it here — that is the
    /// point: the discovery surface can't silently fall out of date.
    #[test]
    fn catalog_covers_builtins() {
        let names = catalog_names();
        for name in BUILTIN_NAMES.iter().chain(OPTIONAL_BUILTIN_NAMES.iter()) {
            assert!(
                names.contains(name),
                "builtin '{name}' is installable but missing from the catalog; \
                 add a CatalogEntry for it in catalog.rs"
            );
        }
    }

    #[test]
    fn catalog_has_no_duplicate_names() {
        let names = catalog_names();
        assert_eq!(
            names.len(),
            CATALOG.len(),
            "duplicate worker name in CATALOG"
        );
    }

    #[test]
    fn every_entry_has_a_known_category() {
        // Every category should be in CATEGORY_ORDER so output ordering is
        // deterministic and intentional rather than alphabetical-by-accident.
        for entry in CATALOG {
            assert!(
                CATEGORY_ORDER.contains(&entry.category),
                "entry '{}' has category '{}' not listed in CATEGORY_ORDER",
                entry.name,
                entry.category
            );
        }
    }

    #[test]
    fn empty_query_matches_everything() {
        for entry in CATALOG {
            assert!(entry_matches(entry, ""));
            assert!(entry_matches(entry, "   "));
        }
    }

    #[test]
    fn query_matches_name_category_and_summary() {
        let queue = CATALOG.iter().find(|e| e.name == "iii-queue").unwrap();
        // by name fragment
        assert!(entry_matches(queue, "queue"));
        // case-insensitive
        assert!(entry_matches(queue, "QUEUE"));
        // by category
        assert!(entry_matches(queue, "messaging"));
        // by summary word
        assert!(entry_matches(queue, "dead-letter"));
        // non-match
        assert!(!entry_matches(queue, "kubernetes"));
    }

    #[test]
    fn grouped_matches_orders_categories_by_rank() {
        let groups = grouped_matches("");
        let order: Vec<&str> = groups.iter().map(|(c, _)| *c).collect();
        // Networking precedes Messaging precedes State & Data, etc.
        let net = order.iter().position(|c| *c == "Networking").unwrap();
        let msg = order.iter().position(|c| *c == "Messaging").unwrap();
        let state = order.iter().position(|c| *c == "State & Data").unwrap();
        assert!(
            net < msg && msg < state,
            "unexpected category order: {order:?}"
        );
    }

    #[test]
    fn grouped_matches_filters_to_one_category() {
        let groups = grouped_matches("messaging");
        assert_eq!(groups.len(), 1);
        assert_eq!(groups[0].0, "Messaging");
        let names: HashSet<&str> = groups[0].1.iter().map(|e| e.name).collect();
        assert!(names.contains("iii-queue"));
        assert!(names.contains("iii-pubsub"));
        assert!(!names.contains("iii-http"));
    }

    #[test]
    fn run_returns_zero_on_match_and_one_on_miss() {
        assert_eq!(run(Some(""), false), 0);
        assert_eq!(run(Some("queue"), true), 0);
        assert_eq!(run(Some("no-such-worker-xyz"), false), 1);
    }
}
