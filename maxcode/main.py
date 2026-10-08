from pathlib import Path
from dotenv import load_dotenv

# Prefer settings from the project being analyzed; use packaged defaults as fallback.
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

from rich.console import Console
from rich.prompt import Prompt
import asyncio
from maxcode.config import config
from maxcode.observability.logger import get_logger
from maxcode.context.indexers.factory import get_indexer, get_index_inspector
from maxcode.llm.factory import get_llm, get_embedder
from maxcode.agent.factory import build_agent
from maxcode.agent.orchestrator import handle_query
from maxcode.memory.session import get_current_session, new_session, switch_session
from maxcode.memory.short_term import get_checkpointer_db_path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver 
console = Console()
logger = get_logger(__name__)


def get_or_create_index():
    repo_path = str(Path.cwd())
    logger.info(f"Checking index for {repo_path}")
    console.print(f"[dim]Checking index for {repo_path}[/dim]")
    return get_indexer()(repo_path)


async def initialize(checkpointer):
    """Boostrap LLM, embedder, and index before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]")
    console.print(f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']} [/dim]")

    index = get_or_create_index()
    agent = await build_agent(checkpointer)
    session_id = get_current_session()
    console.print(f"[dim]Session: {session_id}[/dim]")
    console.print(f"[green]✓ Ready[/green]\n") 
    return llm, embedder, index, agent, session_id


async def _run_async():
    logger.info("Starting MaxCode")
    console.print("\n[bold blue]MaxCode[/bold blue] - RAG-Powered code assistant")
    console.print("Type [bold] '/exit' [/bold] to quit\n")

    async with AsyncSqliteSaver.from_conn_string(get_checkpointer_db_path()) as checkpointer:
        llm, embedder, index, agent, session_id = await initialize(checkpointer)
        console.print(f"Type [bold] '/exit'[/bold] to quit\n")

        while True:
            user_input = Prompt.ask("[bold green]>[/bold green]")
            if not user_input.strip():
                continue
            if user_input.lower() in ("/exit", "/quit"):
                logger.info("Shutting down")
                console.print("[dim]Goodbye![/dim]")
                break
            elif user_input:
                question = user_input.removeprefix("/ask ").strip()
                logger.info(f"Ask command received: {question}")
                console.print(f"[dim] Searching for: {question}...[/dim]")
                response = await handle_query(agent, question, session_id)
                console.print(response)
            elif user_input == "/new_session":
                session_id = new_session()
                console.print(f'[green]New session started: {session_id}[/green]')
            elif user_input.startswith("/switch"):
                target = user_input.removeprefix("/switch").strip()
                session_id = switch_session(target)
                console.print(f"[green]Switched to session: {session_id} [/green]")
            elif user_input == "/session":
                console.print(f"[dim]Current session: {session_id} [/dim]")
            elif user_input == "/show_index":
                logger.info("Showing semantic index")
                get_index_inspector()(index)
            else:
                logger.warning(f"Unknown command received: {user_input}")
                console.print("[yellow]Unknown command. Try:[/yellow]")
                console.print(" [bold]/show_semantic_index[/bold] - show all chunks in the semantic index")
                console.print(" [bold] /ask <question> [/bold] - ask a question")
                console.print("[bold] /show_index [/bold]      -show all chunks in the index")
                console.print("[bold] /new_session[/bold]      - start a fresh conversation")
                console.print("[bold]/switch<session_id>[/bold] - resume a past session")
                console.print("[bold]/session[/bold]   -show current session id")

def run():
    asyncio.run(_run_async())
if __name__ == "__main__":
    run()