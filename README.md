# MaxCode

MaxCode is a terminal-based, retrieval-augmented coding assistant. It indexes the code in the current working directory, retrieves relevant code while answering questions, and can use filesystem, terminal, skill, and configured MCP tools while working on a project.

## Features

- Parses common source languages with Tree-sitter, including Python, JavaScript/TypeScript, Java, Go, Rust, C/C++, C#, Ruby, PHP, Swift, Kotlin, and shell scripts.
- Chunks Markdown, YAML, JSON, TOML, and text files for indexing.
- Supports Qdrant and Chroma vector stores, with dense, sparse, or hybrid Qdrant retrieval.
- Keeps conversation checkpoints in SQLite and supports configured MCP servers, including the GitHub MCP server.

## Requirements

- Python 3.14 or newer (the project requires Python `>=3.14,<4.0`).
- A model API key for the selected language model. The default provider is Gemini.
- An accessible Qdrant server for the default vector-store configuration, or change the configuration to use local Chroma.
- Node.js/npm with `npx` if you want the configured GitHub MCP integration.

The Hugging Face embedding model is downloaded locally the first time it is used. Hybrid Qdrant retrieval also downloads the configured FastEmbed sparse model when needed.

## Install

Clone the repository and install it into a virtual environment:

```shell
git clone https://github.com/sanketsanjaypote29/maxcode.git
cd maxcode
python -m venv .venv
```

Activate the environment, then install MaxCode:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

```shell
# macOS / Linux
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Configure

Create a `.env` file in the directory from which you will launch MaxCode. Values are loaded from the working directory first, then from the installed package directory. Keep real credentials out of source control.

```dotenv
GOOGLE_API_KEY=your-gemini-api-key
QDRANT_URL=http://localhost:6333
# Set this for Qdrant Cloud or another secured Qdrant server.
QDRANT_API_KEY=
# Needed for the configured GitHub MCP server.
GITHUB_TOKEN=your-github-token
```

Start a local Qdrant server separately, for example with Docker:

```shell
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

The GitHub MCP server is configured in `maxcode/maxcode_mcp_server.json` and is started with `npx`. If `npx` is unavailable, MaxCode skips that server. A GitHub token is required to use its authenticated GitHub tools.

## Run

MaxCode indexes the **current working directory**, so launch it from the codebase you want to ask about. The editable install makes the `maxcode` command available while the virtual environment is active.

```shell
cd path/to/project-to-analyze
maxcode
```

Enter a question directly, or prefix it with `/ask`:

```text
Where is the authentication flow implemented?
/ask Explain how the indexer chooses files.
```

Use `/exit` or `/quit` to end the session.

## Configuration

The defaults are in `maxcode/config.yaml`:

- `llm.provider` and `llm.model` select Gemini, Anthropic, or OpenAI chat models. Set the corresponding provider API key in `.env` (`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`).
- `embeddings.provider` selects Hugging Face embeddings by default; other values use OpenAI embeddings and require `OPENAI_API_KEY`.
- `vector_store.provider` selects Qdrant by default. Set it to another value to use Chroma, whose local data directory is configured by `chromadb.persist_dir`.
- `rag.mode` and `vector_store.retrieval_mode` control retrieval. Qdrant supports `dense`, `sparse`, and `hybrid` retrieval modes.
- Collection names, memory paths, and summarization limits are configurable in the same file.

## Local Data and Permissions

By default, MaxCode stores its SQLite conversation checkpoint and current session ID under `.maxcode/memory/`. Chroma data is stored under `.maxcode/chromadb/` when Chroma is selected. Qdrant data is stored by the configured Qdrant service. These local paths are ignored by Git.

The agent has tools that can run terminal commands and read, write, append, and delete files in the working project. Use it with codebases you trust, and review requested commands and file changes before approving or relying on them. Give `GITHUB_TOKEN` only the permissions needed for your intended GitHub tasks.