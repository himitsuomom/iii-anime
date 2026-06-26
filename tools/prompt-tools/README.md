# Prompt tools — GitHub stars list「プロンプト」

This directory installs the **runnable tools** from the GitHub stars list
[`himitsuomom/lists/プロンプト`](https://github.com/stars/himitsuomom/lists/%E3%83%97%E3%83%AD%E3%83%B3%E3%83%97%E3%83%88).

## Quick start

```bash
bash tools/prompt-tools/install.sh
# then add the Go bin dir to your PATH for Fabric:
export PATH="$HOME/go/bin:$PATH"
fabric --version
```

## What's in the list (12 repositories)

The list mixes two kinds of repositories. Only the **tools** are installable;
the **prompt collections** are Markdown/data you browse or copy from.

### Installable tools

| Repository | Type | Installed by `install.sh` |
| --- | --- | --- |
| [danielmiessler/Fabric](https://github.com/danielmiessler/Fabric) | Go CLI | ✅ `go install` → `~/go/bin/fabric` |
| [promptslab/Promptify](https://github.com/promptslab/Promptify) | Python library | ✅ venv at `~/.venvs/prompt-tools` |
| [bigscience-workshop/promptsource](https://github.com/bigscience-workshop/promptsource) | Python library/app | ❌ see note below |

> **promptsource is not installed automatically.** Its PyPI sdist is broken
> (missing `requirements.txt`) and it is only reliably installable from its
> GitHub git repo. In this remote environment, `github.com` git access is
> blocked by the egress policy (HTTP 403), so it must be installed on a machine
> with GitHub access:
> ```bash
> pip install "git+https://github.com/bigscience-workshop/promptsource.git"  # needs Python 3.7–3.9
> ```

### Prompt collections (not installable — reference material)

These are curated prompt libraries; clone or browse them as needed.

- [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools)
- [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks)
- [dahatake/GenerativeAI-Prompt-Sample-Japanese](https://github.com/dahatake/GenerativeAI-Prompt-Sample-Japanese)
- [0xeb/TheBigPromptLibrary](https://github.com/0xeb/TheBigPromptLibrary)
- [abilzerian/LLM-Prompt-Library](https://github.com/abilzerian/LLM-Prompt-Library)
- [promptslab/Awesome-Prompt-Engineering](https://github.com/promptslab/Awesome-Prompt-Engineering)
- [MrXie23/PromptLibrary](https://github.com/MrXie23/PromptLibrary)
- [f/prompts.chat](https://github.com/f/prompts.chat)
- [shareAI-lab/share-best-prompt](https://github.com/shareAI-lab/share-best-prompt)

## Usage notes

**Fabric** — needs an API key (e.g. `OPENAI_API_KEY`) and a one-time setup:
```bash
fabric --setup
echo "summarize this" | fabric --pattern summarize
```

**Promptify** — imported as a library (no CLI):
```bash
~/.venvs/prompt-tools/bin/python - <<'PY'
from promptify import Prompter, OpenAI, Pipeline
print("Promptify ready")
PY
```
