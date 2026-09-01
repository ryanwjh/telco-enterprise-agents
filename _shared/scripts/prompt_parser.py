"""Prompt Parser and Domain Resolver for Telco Enterprise Agents.

Extracts 3 curated prompts from an agent's README.md (from Sample Q&A or Example Questions).
"""

import re
from pathlib import Path
import yaml

def resolve_agent_domain(agent_name: str, repo_root: Path | None = None) -> str:
    """Resolves the telco domain name for a given agent name."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
    
    # 1. Try checking table_registry.yaml
    registry_file = repo_root / "_shared" / "table_registry.yaml"
    if registry_file.exists():
        try:
            data = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
            agents_map = data.get("agents", {})
            if agent_name in agents_map:
                return agents_map[agent_name].get("domain", "")
        except Exception:
            pass
            
    # 2. Try file system lookup
    matching_dirs = list((repo_root / "domains").glob(f"*/agents/{agent_name}"))
    if matching_dirs:
        return matching_dirs[0].parent.parent.name
        
    raise ValueError(f"Could not find agent '{agent_name}' in repository under domains/*/agents/{agent_name}")


def parse_agent_prompts(readme_path: Path) -> list[str]:
    """Parses at least 3 curated prompts from an agent's README.md."""
    if not readme_path.exists():
        raise FileNotFoundError(f"Agent README not found at {readme_path}")
        
    content = readme_path.read_text(encoding="utf-8")
    prompts = []
    
    # Pattern 1: > **User Prompt:** "..."
    for p in re.findall(r'>\s*\*\*User Prompt:\*\*\s*["“](.*?)["”]', content, re.MULTILINE):
        cleaned = p.strip()
        if cleaned and not cleaned.startswith("TODO") and cleaned not in prompts:
            prompts.append(cleaned)
            
    # Pattern 2: *Question:* "..." or **Question:** "..."
    for p in re.findall(r'[\*\_]{1,2}Question:[\*\_]{1,2}\s*["“](.*?)["”]', content, re.MULTILINE):
        cleaned = p.strip()
        if cleaned and not cleaned.startswith("TODO") and cleaned not in prompts:
            prompts.append(cleaned)
            
    # Pattern 3: Numbered or bulleted example questions: 1. "..." or - "..."
    ex_match = re.search(r'##\s+(?:(?:\d+\.\s+)?(?:Real\s+)?Example Questions).*?(?=\n##\s+|\Z)', content, re.DOTALL | re.IGNORECASE)
    if ex_match:
        for p in re.findall(r'(?:^\s*(?:\d+\.|\-)\s*["“](.*?)["”])', ex_match.group(0), re.MULTILINE):
            cleaned = p.strip()
            if cleaned and not cleaned.startswith("TODO") and cleaned not in prompts:
                prompts.append(cleaned)
                
    if len(prompts) < 3:
        raise ValueError(
            f"Expected at least 3 curated prompts in {readme_path}, but found {len(prompts)}: {prompts}"
        )
        
    return prompts[:3]
