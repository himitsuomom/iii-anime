//! Integration coverage for the in-repo `templates/iii` template store, which
//! holds two kinds of templates (both intent-orchestrated):
//!   - Docker Compose stacks (`scripts/import-compose-templates.py`)
//!   - Reference / knowledge packs from awesome-lists
//!     (`scripts/import-awesome-lists.py`), tagged `kind:reference`.
//!
//! These tests treat that directory as a Local template source and verify that
//! every registered template loads, scaffolds end to end (its manifest files
//! land on disk with no language selected), and is rank-able by the
//! orchestrator. Kind-specific invariants (compose ⇒ a compose file + Docker;
//! reference ⇒ RESOURCES.md + index.yaml, no Docker) are checked per kind.

use scaffolder_core::{
    LanguageFiles, Selection, SelectionQuery, TemplateEntry, TemplateFetcher, TemplateManifest,
    auto_select, copy_template, rank,
};
use std::path::PathBuf;
use tempfile::TempDir;

/// Load every registered template as an orchestrator [`TemplateEntry`].
async fn load_catalog(fetcher: &mut TemplateFetcher) -> Vec<TemplateEntry> {
    let root = fetcher.fetch_root_manifest().await.unwrap();
    let mut catalog = Vec::new();
    for name in &root.templates {
        let manifest = fetcher.fetch_template_manifest(name).await.unwrap();
        catalog.push(TemplateEntry::from_manifest(name, &manifest));
    }
    catalog
}

/// Reference (knowledge-pack) templates carry the `kind:reference` tag; compose
/// stacks do not.
fn is_reference(manifest: &TemplateManifest) -> bool {
    manifest
        .selection
        .tags
        .iter()
        .any(|t| t == "kind:reference")
}

/// Absolute path to the repo's `templates/iii` product directory.
fn templates_dir() -> PathBuf {
    // CARGO_MANIFEST_DIR -> crates/scaffolder-core
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../templates/iii")
        .canonicalize()
        .expect("templates/iii directory should exist at the repo root")
}

#[tokio::test]
async fn root_manifest_registers_expected_compose_samples() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let root = fetcher.fetch_root_manifest().await.unwrap();

    assert!(!root.templates.is_empty(), "no templates registered");
    for expected in ["fastapi", "nginx-nodejs-redis", "django", "wordpress-mysql"] {
        assert!(
            root.templates.iter().any(|t| t == expected),
            "root manifest missing '{expected}'; has: {:?}",
            root.templates
        );
    }
}

#[tokio::test]
async fn every_registered_template_scaffolds_with_no_language_selected() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let root = fetcher.fetch_root_manifest().await.unwrap();

    for name in &root.templates {
        let manifest = fetcher
            .fetch_template_manifest(name)
            .await
            .unwrap_or_else(|e| panic!("manifest for '{name}' failed to load: {e}"));

        // Mirror the CLI: merge root language patterns with per-template ones.
        let mut language_files: LanguageFiles = root.language_files.clone();
        language_files.merge(&manifest.language_files);

        let out = TempDir::new().unwrap();
        // Compose samples gate nothing on language, so an empty selection must
        // still copy the whole stack.
        let copied = copy_template(
            &mut fetcher,
            name,
            &manifest,
            out.path(),
            &[],
            &language_files,
        )
        .await
        .unwrap_or_else(|e| panic!("scaffolding '{name}' failed: {e}"));

        assert!(
            !copied.is_empty(),
            "template '{name}' copied zero files (language gating dropped everything?)"
        );

        // Compose stacks must yield a compose file; reference packs need not.
        if !is_reference(&manifest) {
            let has_compose = ["compose.yaml", "compose.yml", "docker-compose.yml"]
                .iter()
                .any(|f| out.path().join(f).exists());
            assert!(
                has_compose,
                "compose template '{name}' did not produce a compose file"
            );
        }

        // Every file the manifest promised must exist on disk.
        for file in &manifest.files {
            assert!(
                out.path().join(file).exists(),
                "template '{name}' missing expected file '{file}'"
            );
        }
    }
}

#[tokio::test]
async fn every_template_carries_selection_metadata() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let catalog = load_catalog(&mut fetcher).await;

    for entry in &catalog {
        assert!(
            !entry.profile.tags.is_empty(),
            "template '{}' has no selection tags",
            entry.name
        );
        assert!(
            !entry.profile.use_cases.is_empty(),
            "template '{}' has no use cases",
            entry.name
        );
        // Kind invariant: compose stacks require Docker, reference packs don't.
        let reference = entry.profile.tags.iter().any(|t| t == "kind:reference");
        assert_eq!(
            entry.profile.conditions.requires_docker, !reference,
            "template '{}' requires_docker should be {} (reference={reference})",
            entry.name, !reference
        );
    }
}

#[tokio::test]
async fn reference_templates_scaffold_resources_and_index() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let root = fetcher.fetch_root_manifest().await.unwrap();

    let mut seen_reference = 0;
    for name in &root.templates {
        let manifest = fetcher.fetch_template_manifest(name).await.unwrap();
        if !is_reference(&manifest) {
            continue;
        }
        seen_reference += 1;

        let mut language_files: LanguageFiles = root.language_files.clone();
        language_files.merge(&manifest.language_files);
        let out = TempDir::new().unwrap();
        copy_template(
            &mut fetcher,
            name,
            &manifest,
            out.path(),
            &[],
            &language_files,
        )
        .await
        .unwrap_or_else(|e| panic!("scaffolding reference '{name}' failed: {e}"));

        assert!(
            out.path().join("RESOURCES.md").exists(),
            "reference template '{name}' missing RESOURCES.md"
        );
        assert!(
            out.path().join("index.yaml").exists(),
            "reference template '{name}' missing index.yaml"
        );
        assert!(
            !manifest.selection.conditions.requires_docker,
            "reference template '{name}' should not require docker"
        );
    }

    assert!(
        seen_reference >= 20,
        "expected the imported awesome-list catalog, saw only {seen_reference} reference templates"
    );
}

#[tokio::test]
async fn orchestrator_ranks_expected_template_first_for_intents() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let catalog = load_catalog(&mut fetcher).await;

    // (intent, expected top-ranked catalog name) over the real catalog. The
    // top of the ranking is the orchestrator's contract; whether it's a
    // confident auto-pick vs. an ambiguous shortlist is a UX threshold.
    let cases = [
        (
            "a Go REST API with a postgres database",
            "nginx-golang-postgres",
        ),
        (
            "node web app that needs a redis cache",
            "nginx-nodejs-redis",
        ),
        (
            "metrics monitoring with grafana dashboards",
            "prometheus-grafana",
        ),
        ("a wordpress blog", "wordpress-mysql"),
        ("django python web application", "django"),
    ];

    for (intent, expected) in cases {
        let ranked = rank(&catalog, &SelectionQuery::from_intent(intent));
        let top = ranked
            .first()
            .unwrap_or_else(|| panic!("intent '{intent}' matched nothing; expected '{expected}'"));
        assert_eq!(
            top.name,
            expected,
            "intent '{intent}' should rank '{expected}' first, got {:?}",
            ranked
                .iter()
                .map(|r| (&r.name, r.score))
                .collect::<Vec<_>>()
        );
    }
}

#[tokio::test]
async fn orchestrator_confidently_auto_selects_distinctive_intents() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let catalog = load_catalog(&mut fetcher).await;

    // Intents distinctive enough that exactly one template stands out.
    let cases = [
        (
            "node web app that needs a redis cache",
            "nginx-nodejs-redis",
        ),
        (
            "metrics monitoring with grafana dashboards",
            "prometheus-grafana",
        ),
    ];

    for (intent, expected) in cases {
        match auto_select(&catalog, &SelectionQuery::from_intent(intent)) {
            Selection::Confident(rec) => assert_eq!(
                rec.name, expected,
                "intent '{intent}' should confidently pick '{expected}'"
            ),
            other => panic!("intent '{intent}' expected confident '{expected}', got {other:?}"),
        }
    }
}

#[tokio::test]
async fn orchestrator_ranks_reference_lists_for_domain_intents() {
    let mut fetcher = TemplateFetcher::from_local(templates_dir(), "test");
    let catalog = load_catalog(&mut fetcher).await;

    // Domain/resource intents should surface the right awesome-list reference
    // template at the top of the ranking. Intents are chosen to be distinctive
    // enough to clear the inherent overlaps (two react / two ios / two mac lists).
    let cases = [
        ("curated python libraries and frameworks", "awesome-python"),
        ("selfhosted privacy homelab tools", "awesome-selfhosted"),
        ("react component libraries", "awesome-react-components"),
        (
            "software design patterns and architecture",
            "awesome-design-patterns",
        ),
        ("open source ios apps", "open-source-ios-apps"),
        ("curated golang libraries and frameworks", "awesome-go"),
    ];

    for (intent, expected) in cases {
        let ranked = rank(&catalog, &SelectionQuery::from_intent(intent));
        let top = ranked
            .first()
            .unwrap_or_else(|| panic!("intent '{intent}' matched nothing; expected '{expected}'"));
        assert_eq!(
            top.name,
            expected,
            "intent '{intent}' should rank '{expected}' first, got {:?}",
            ranked
                .iter()
                .take(4)
                .map(|r| (&r.name, r.score))
                .collect::<Vec<_>>()
        );
    }
}
