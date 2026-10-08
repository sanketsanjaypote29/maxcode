from __future__ import annotations
import re
from pathlib import Path
from maxcode.observability.logger import get_logger
logger = get_logger(__name__)



# Every skill package must have this file at its root.
# Folder inside skills_dir that lack this file are skipped entirely.


SKILL_FILENAME = "SKILL.md"


class SkillNotFoundError(Exception):
    pass

class SkillRegistry:
    """Owns the in-memory catalog of all skills found in skills_dir. 
 
   Expected layout on disk: 
       skills_dir/ 
           python_debug/ 
               SKILL.md          ← required — frontmatter + instructions 
               scripts/          ← optional — executable helpers 
               templates/        ← optional — output templates 
               resources/        ← optional — reference docs 
           write_tests/ 
               SKILL.md 
               templates/ 
                   pytest_template.py 
 
   After calling load(), the internal _skills dict looks like: 
       { 
           "python_debug": { 
               "meta":      {"name": "python_debug", "description": "...", ...}, 
               "body":      "You are an expert Python debugger. Follow these steps...", 
               "skill_dir": Path(".educosys/skills/python_debug") 
           }, 
           "write_tests": { 
               "meta":      {"name": "write_tests", "description": "...", ...}, 
               "body":      "Generate pytest unit tests...", 
               "skill_dir": Path(".educosys/skills/write_tests") 
           } 
       } 
 
   "meta" is parsed from the YAML frontmatter block (name, description, when_to_use, ...). 
   "body" is everything after the frontmatter — the actual instructions sent to the LLM. 
   "skill_dir" is kept so we can later discover support files inside that folder. 
   """

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self._skills: dict[str, dict] = {}

        #------------------------------------------------------------------ 
        # Startup: scan disk and populate _skills 
        # ------------------------------------------------------------------

    def load(self) -> None:
        """Walk skills_dir and parse every skill.md found.
        Called once at agent startup via get_registry() in skill_tools.py
        Safe to call again to hot-reload if skills change on disk."""

        self._skills.clear()

        if not self._skills_dir.exists():
            logger.warning(f"skills_dir not found. {self._skills_dir}. No skills loaded. ")
            return

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue #skip stray files at the top lvevl of skills_dir

            skill_file = skill_dir / SKILL_FILENAME
            if not skill_file.exists():
                logger.warning(f"Skipping {skill_dir.name}: no SKILL.md found") 
                continue

            try:
                meta, body = _parse_skill_file(skill_file)
                # Use "name" function from frontmatter if declared; fall back to the folder name.
                # This means the folder name and the frontmatter name should match,
                # but the frontmatter value is what the agent will refre to.

                name = meta.get("name", skill_dir.name)
                self._skills[name] = {
                    "meta": meta, #dict of frontmatter fields
                    "body": body, #raw instruction text (sent to llm on activation)
                    "skill_dir": skill_dir, #kept for support file discovery
                }
                logger.info(f"Loaded skill: {name}")
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_dir.name}: {e}")

    def build_skills_prompt(self) -> str:
        """Return skill metadata for the agent prompt without including full bodies."""
        if not self._skills:
            return ""

        lines = ["=== Available skills ==="]
        for name, skill in self._skills.items():
            meta = skill["meta"]
            description = meta.get("description", "")
            when_to_use = meta.get("when_to_use")
            entry = f"- {name}: {description}"
            if when_to_use:
                entry += f" | when_to_use: {when_to_use}"
            lines.append(entry)

        lines.append("When a request matches a skill, call load_skill(name) for its instructions.")
        return "\n".join(lines)

    def load_skill(self, name: str) -> str:
        """Return a skill's full instructions and the paths of its support files."""
        if name not in self._skills:
            available = ", ".join(self._skills) or "none"
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {available}"
            )

        skill = self._skills[name]
        support_files = _list_support_files(skill["skill_dir"])
        result = skill["body"]
        if support_files:
            result += "\n\n--- Support files available ---\n"
            result += "\n".join(support_files)
            result += "\nRead relevant support files with the read_file tool."
        return result

    @property
    def skill_names(self) -> list[str]:
        return list(self._skills.keys())



# --------------------------------------------------------------------------- 
# Module-level helpers (private to this file) 
# --------------------------------------------------------------------------- 

def _parse_skill_file(path: Path) -> tuple[dict, str]:
    """
    Read a SKILL.md and split it into (frontmatter_dict, body_str)
    A valid SKILL.md looks like: 
        --- 
        name: python_debug 
        description: Debug Python errors and tracebacks 
        when_to_use: error, traceback, exception 
        --- 
        You are an expert Python debugger...   ← this is the body 
    
    The regex matches the opening ---, captures everything up to the closing ---, 
    then captures the rest of the file as the body. 
    If there is no frontmatter, the entire file is treated as the body and 
    meta is returned as an empty dict (the folder name becomes the skill name). 
    """ 
    text = path.read_text(encoding="utf-8")

    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", text, re.DOTALL)
    if not match:
        # No frontmatter block found - body is the whole file.
        return {}, text.strip()

    frontmatter_str = match.group(1) # raw yaml text between the --- markers
    body = match.group(2).strip()    # everything after the closing ---
    meta = _parse_yaml(frontmatter_str)
    return meta, body


def _parse_yaml(text: str) -> dict:
    """
   Parse the frontmatter YAML string into a dict. 
 
   Strategy: 
     1. Try yaml.safe_load (pyyaml is already a dependency via config.py). 
     2. If yaml isn't importable for any reason, fall back to a line-by-line 
        parser that handles flat "key: value" pairs only (no nesting or lists). 
        This is enough for the required frontmatter fields. 
   """ 
    try:
        import yaml # already present - loaded by config.py at startup
        return yaml.safe_load(text) or {}

    except ImportError:
        pass

    # Minimal fallback for flat key: value frontmatter
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _list_support_files(skill_dir: Path) -> list[str]:
    """ 
   Return the absolute paths of every file inside the skill folder except SKILL.md. 
 
   rglob("*") descends into all subdirectories (scripts/, templates/, resources/, ...), 
   so the agent gets a complete picture of what resources the skill package ships with. 
 
 
   Example for python_debug/: 
       [ 
           "/path/to/skills/python_debug/scripts/run_debugger.py", 
           "/path/to/skills/python_debug/resources/common_errors.md" 
       ] 
   """ 
    files = []
    for f in skill_dir.rglob("*"):
        if f.is_file() and f.name != SKILL_FILENAME:
            files.append(str(f))

    return files


    