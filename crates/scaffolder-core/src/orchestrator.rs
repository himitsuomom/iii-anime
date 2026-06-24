//! Intent-driven template orchestration.
//!
//! Given a free-text intent ("a Go REST API with a Postgres database") and/or
//! explicit tags, the orchestrator scores every template in the catalog by how
//! well its [`SelectionProfile`] matches, then either auto-selects a confident
//! winner or surfaces a ranked shortlist for the user to choose from.
//!
//! The scoring is deliberately simple, deterministic, and dependency-free:
//! tokenize the intent, match tokens against each template's tags, keywords,
//! use-cases, and descriptive text (in that priority order), add weight for
//! preferred tags, and hard-filter on required tags and conditions.
//!
//! [`SelectionProfile`]: crate::templates::manifest::SelectionProfile

use crate::templates::manifest::{SelectionProfile, TemplateManifest};
use std::collections::HashSet;

// Per-token score contributions, highest-signal first. A token scores at most
// once per template, taking the strongest bucket it lands in.
const SCORE_TAG: f32 = 3.0;
const SCORE_KEYWORD: f32 = 2.5;
const SCORE_USE_CASE: f32 = 1.5;
const SCORE_TEXT: f32 = 0.6;
/// Weight added for each satisfied `preferred_tag`.
const SCORE_PREFERRED_TAG: f32 = 2.0;

/// Minimum score for the top candidate to be auto-selected without asking.
const CONFIDENT_MIN_SCORE: f32 = 2.5;
/// Minimum lead the top candidate must have over the runner-up to be confident.
const CONFIDENT_MARGIN: f32 = 1.0;
/// How many candidates to surface when the result is ambiguous.
const SHORTLIST_LEN: usize = 5;

/// Tokens too generic to carry selection signal.
const STOPWORDS: &[&str] = &[
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "for",
    "to",
    "with",
    "in",
    "on",
    "my",
    "me",
    "i",
    "we",
    "is",
    "it",
    "that",
    "this",
    "app",
    "application",
    "stack",
    "want",
    "need",
    "using",
    "use",
    "project",
    "service",
    "server",
    "build",
    "create",
    "make",
    "set",
    "up",
    "new",
];

/// One template the orchestrator can choose from.
#[derive(Debug, Clone)]
pub struct TemplateEntry {
    /// Catalog name (the directory / `--template` value).
    pub name: String,
    /// Human-readable display name from the manifest.
    pub display_name: String,
    /// One-line description from the manifest.
    pub description: String,
    /// Structured selection metadata.
    pub profile: SelectionProfile,
}

impl TemplateEntry {
    /// Build an entry from a catalog name and its manifest.
    pub fn from_manifest(name: impl Into<String>, manifest: &TemplateManifest) -> Self {
        Self {
            name: name.into(),
            display_name: manifest.name.clone(),
            description: manifest.description.clone(),
            profile: manifest.selection.clone(),
        }
    }
}

/// What the user is looking for.
#[derive(Debug, Clone, Default)]
pub struct SelectionQuery {
    /// Free-text intent / use-case description.
    pub intent: String,
    /// Tags that MUST be present (hard filter). Empty = no hard requirement.
    pub required_tags: Vec<String>,
    /// Tags that add weight when present.
    pub preferred_tags: Vec<String>,
    /// Whether Docker is available in the target environment. `None` = unknown
    /// (don't filter); `Some(false)` excludes templates that require Docker.
    pub docker_available: Option<bool>,
}

impl SelectionQuery {
    /// Build a query from a free-text intent.
    pub fn from_intent(intent: impl Into<String>) -> Self {
        Self {
            intent: intent.into(),
            ..Default::default()
        }
    }

    /// Add hard-required tags.
    pub fn require_tags<I, S>(mut self, tags: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.required_tags
            .extend(tags.into_iter().map(|t| t.into().to_lowercase()));
        self
    }

    /// Add preferred (weighted) tags.
    pub fn prefer_tags<I, S>(mut self, tags: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.preferred_tags
            .extend(tags.into_iter().map(|t| t.into().to_lowercase()));
        self
    }
}

/// A scored recommendation.
#[derive(Debug, Clone)]
pub struct Recommendation {
    /// Catalog name to pass to the scaffolder.
    pub name: String,
    /// Human-readable display name.
    pub display_name: String,
    /// Match score (higher is better).
    pub score: f32,
    /// Human-readable reasons the template matched, best first.
    pub reasons: Vec<String>,
}

/// Outcome of [`auto_select`].
#[derive(Debug, Clone)]
pub enum Selection {
    /// One clear winner — safe to scaffold without asking.
    Confident(Recommendation),
    /// Several plausible candidates — let the user choose among these.
    Ambiguous(Vec<Recommendation>),
    /// Nothing matched the query.
    NoMatch,
}

/// Lowercase, split on non-alphanumerics, drop stopwords and 1-char tokens.
fn tokenize(text: &str) -> Vec<String> {
    text.split(|c: char| !c.is_alphanumeric())
        .map(|w| w.to_lowercase())
        .filter(|w| w.len() > 1 && !STOPWORDS.contains(&w.as_str()))
        .collect()
}

/// All matchable tag forms: the full tag plus the part after `:`.
fn tag_forms(tags: &[String]) -> HashSet<String> {
    let mut set = HashSet::new();
    for tag in tags {
        let lower = tag.to_lowercase();
        if let Some((_, value)) = lower.split_once(':') {
            set.insert(value.to_string());
        }
        set.insert(lower);
    }
    set
}

/// Score one template against the query. Returns `None` when a hard filter
/// (required tag or unsatisfiable condition) excludes the template.
fn score_entry(entry: &TemplateEntry, query: &SelectionQuery) -> Option<Recommendation> {
    let tags = tag_forms(&entry.profile.tags);

    // Hard filter: every required tag must be present.
    for req in &query.required_tags {
        if !tags.contains(req) {
            return None;
        }
    }

    // Hard filter: respect a known-unavailable Docker environment.
    if query.docker_available == Some(false) && entry.profile.conditions.requires_docker {
        return None;
    }

    let keywords: HashSet<String> = entry
        .profile
        .keywords
        .iter()
        .map(|k| k.to_lowercase())
        .collect();
    let use_case_tokens: HashSet<String> = entry
        .profile
        .use_cases
        .iter()
        .flat_map(|u| tokenize(u))
        .collect();
    let text_tokens: HashSet<String> = tokenize(&entry.display_name)
        .into_iter()
        .chain(tokenize(&entry.description))
        .collect();

    let mut score = 0.0;
    let mut reasons: Vec<String> = Vec::new();
    let mut matched_tags: Vec<String> = Vec::new();
    let mut matched_keywords: Vec<String> = Vec::new();

    // Each intent token scores once, in the strongest bucket it lands in.
    let mut seen = HashSet::new();
    for token in tokenize(&query.intent) {
        if !seen.insert(token.clone()) {
            continue;
        }
        if tags.contains(&token) {
            score += SCORE_TAG;
            matched_tags.push(token);
        } else if keywords.contains(&token) {
            score += SCORE_KEYWORD;
            matched_keywords.push(token);
        } else if use_case_tokens.contains(&token) {
            score += SCORE_USE_CASE;
        } else if text_tokens.contains(&token) {
            score += SCORE_TEXT;
        }
    }

    if !matched_tags.is_empty() {
        reasons.push(format!("matches stack: {}", matched_tags.join(", ")));
    }
    if !matched_keywords.is_empty() {
        reasons.push(format!("keywords: {}", matched_keywords.join(", ")));
    }

    // Preferred tags add weight regardless of the intent text.
    let mut satisfied_preferred: Vec<String> = Vec::new();
    for pref in &query.preferred_tags {
        if tags.contains(pref) {
            score += SCORE_PREFERRED_TAG;
            satisfied_preferred.push(pref.clone());
        }
    }
    if !satisfied_preferred.is_empty() {
        reasons.push(format!("preferred: {}", satisfied_preferred.join(", ")));
    }

    if score <= 0.0 {
        return None;
    }

    // Surface the best-fit use-case as a reason when we have one.
    if let Some(use_case) = entry.profile.use_cases.first() {
        reasons.push(format!("use case: {use_case}"));
    }

    Some(Recommendation {
        name: entry.name.clone(),
        display_name: entry.display_name.clone(),
        score,
        reasons,
    })
}

/// Rank every catalog entry against the query, best first. Entries excluded by
/// a hard filter or with no positive score are omitted.
pub fn rank(catalog: &[TemplateEntry], query: &SelectionQuery) -> Vec<Recommendation> {
    let mut recs: Vec<Recommendation> = catalog
        .iter()
        .filter_map(|e| score_entry(e, query))
        .collect();
    // Highest score first; ties broken by name for deterministic output.
    recs.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.name.cmp(&b.name))
    });
    recs
}

/// Rank, then decide whether the top candidate is a confident pick, the result
/// is ambiguous, or nothing matched.
pub fn auto_select(catalog: &[TemplateEntry], query: &SelectionQuery) -> Selection {
    let ranked = rank(catalog, query);
    let Some(top) = ranked.first().cloned() else {
        return Selection::NoMatch;
    };

    let runner_up = ranked.get(1).map(|r| r.score).unwrap_or(0.0);
    let confident = top.score >= CONFIDENT_MIN_SCORE && (top.score - runner_up) >= CONFIDENT_MARGIN;

    if confident {
        Selection::Confident(top)
    } else {
        Selection::Ambiguous(ranked.into_iter().take(SHORTLIST_LEN).collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::templates::manifest::SelectionConditions;

    fn entry(
        name: &str,
        display: &str,
        tags: &[&str],
        keywords: &[&str],
        use_cases: &[&str],
        requires_docker: bool,
    ) -> TemplateEntry {
        TemplateEntry {
            name: name.to_string(),
            display_name: display.to_string(),
            description: String::new(),
            profile: SelectionProfile {
                use_cases: use_cases.iter().map(|s| s.to_string()).collect(),
                tags: tags.iter().map(|s| s.to_string()).collect(),
                keywords: keywords.iter().map(|s| s.to_string()).collect(),
                conditions: SelectionConditions {
                    requires_docker,
                    ..Default::default()
                },
            },
        }
    }

    fn catalog() -> Vec<TemplateEntry> {
        vec![
            entry(
                "nginx-golang-postgres",
                "NGINX / Go / PostgreSQL",
                &["web", "api", "lang:go", "proxy:nginx", "db:postgres"],
                &["golang", "postgresql", "nginx", "rest", "relational"],
                &["Go REST API behind an Nginx proxy with a Postgres database"],
                true,
            ),
            entry(
                "nginx-nodejs-redis",
                "NGINX / Node.js / Redis",
                &["web", "lang:node", "proxy:nginx", "cache:redis"],
                &["nodejs", "redis", "nginx", "cache", "javascript"],
                &["Node.js web app with an Nginx proxy and Redis cache"],
                true,
            ),
            entry(
                "prometheus-grafana",
                "Prometheus / Grafana",
                &["monitoring", "metrics", "dashboards"],
                &["prometheus", "grafana", "observability"],
                &["Metrics monitoring with Prometheus and Grafana dashboards"],
                true,
            ),
            entry(
                "wordpress-mysql",
                "WordPress / MySQL",
                &["web", "cms", "db:mysql"],
                &["wordpress", "blog", "php", "mysql"],
                &["WordPress CMS backed by MySQL"],
                true,
            ),
        ]
    }

    #[test]
    fn confident_pick_for_clear_intent() {
        let sel = auto_select(
            &catalog(),
            &SelectionQuery::from_intent("a Go REST API backed by a Postgres database"),
        );
        match sel {
            Selection::Confident(rec) => assert_eq!(rec.name, "nginx-golang-postgres"),
            other => panic!("expected confident pick, got {other:?}"),
        }
    }

    #[test]
    fn keyword_synonym_matches() {
        // "observability" is only a keyword, not a tag.
        let ranked = rank(
            &catalog(),
            &SelectionQuery::from_intent("observability dashboards"),
        );
        assert_eq!(ranked.first().unwrap().name, "prometheus-grafana");
    }

    #[test]
    fn redis_cache_intent_picks_node_redis() {
        let sel = auto_select(
            &catalog(),
            &SelectionQuery::from_intent("web app that needs a redis cache"),
        );
        match sel {
            Selection::Confident(rec) => assert_eq!(rec.name, "nginx-nodejs-redis"),
            other => panic!("expected confident pick, got {other:?}"),
        }
    }

    #[test]
    fn no_match_returns_no_match() {
        let sel = auto_select(
            &catalog(),
            &SelectionQuery::from_intent("quantum blockchain machine learning"),
        );
        assert!(matches!(sel, Selection::NoMatch));
    }

    #[test]
    fn required_tag_hard_filters() {
        // Require mysql: only WordPress qualifies even though the intent leans web.
        let ranked = rank(
            &catalog(),
            &SelectionQuery::from_intent("web database").require_tags(["db:mysql"]),
        );
        assert_eq!(ranked.len(), 1);
        assert_eq!(ranked[0].name, "wordpress-mysql");
    }

    #[test]
    fn docker_unavailable_excludes_docker_templates() {
        let mut query = SelectionQuery::from_intent("go postgres api");
        query.docker_available = Some(false);
        assert!(matches!(
            auto_select(&catalog(), &query),
            Selection::NoMatch
        ));
    }

    #[test]
    fn preferred_tags_break_ties() {
        // Generic intent; prefer redis caching to pull node-redis to the top.
        let ranked = rank(
            &catalog(),
            &SelectionQuery::from_intent("web").prefer_tags(["cache:redis"]),
        );
        assert_eq!(ranked.first().unwrap().name, "nginx-nodejs-redis");
    }

    #[test]
    fn ambiguous_when_multiple_plausible() {
        // "web" alone matches several templates with equal weight.
        let sel = auto_select(&catalog(), &SelectionQuery::from_intent("web"));
        match sel {
            Selection::Ambiguous(list) => assert!(list.len() >= 2),
            other => panic!("expected ambiguous, got {other:?}"),
        }
    }
}
