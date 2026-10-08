from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from maxcode.mcp.maxcode_mcp_client import get_maxcode_mcp_tools
from maxcode.llm.factory import get_llm
from maxcode.agent.tools import search_codebase
from maxcode.memory.short_term import get_checkpointer
from maxcode.observability.logger import get_logger
from maxcode.memory.short_term import get_summarization_middleware
from maxcode.agent.terminal_tools import run_command, run_in_directory
from maxcode.agent.filesystem_tools import (
    read_file,
    write_file,
    append_file,
    delete_file,
    list_directory,
    file_exists
)
from maxcode.skills.skill_tools import load_skill, build_skills_prompt


logger =  get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
For questions about the local codebase, use the search_codebase tool before answering.
For GitHub tasks, use the relevant GitHub MCP tools available to you, such as searching repositories or code, reading files, and working with issues and pull requests.
Do not claim that MCP tools are unavailable merely because you are an AI or chat interface. If a tool call fails, report the actual error and clearly state what could not be completed; never imply that an unsuccessful operation succeeded.
Reference specific file names, function names, and line numbers in codebase answers.
If you cannot find an answer in the codebase, say so explicitly."""



async def build_agent(checkpointer):
    """Create and return a LangChain agent."""
    llm = get_llm()
    mcp_tools = await get_maxcode_mcp_tools()

    skills_prompt = build_skills_prompt()
    full_prompt = SYSTEM_PROMPT
    if skills_prompt:
        full_prompt = SYSTEM_PROMPT  + "\n\n" + skills_prompt

    tools = [search_codebase,
             run_in_directory,
             run_command,
             read_file,
             delete_file,
             file_exists,
             append_file,
             list_directory,
             *mcp_tools
             ]
    middleware = get_summarization_middleware()
    logger.info("Creating agent")
    return create_agent(llm,
                        tools = tools,
                        system_prompt=full_prompt,
                        checkpointer=checkpointer,
                        middleware=[middleware])

