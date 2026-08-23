#!/usr/bin/env python3
"""Generates a new logical agent folder from the shared template.

Usage:
    uv run python _shared/scripts/scaffold_logical_agent.py \
        --domain merchandising --name assortment_planning \
        --display-name "Assortment Planning"
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "_shared" / "templates" / "logical_agent"
INSTRUCTIONS_DIR = REPO_ROOT / "_shared" / "instructions"

INSTRUCTION_FRAGMENT_FILES = [
    "persona_telco_analyst.md",
    "safety_and_grounding_rules.md",
    "output_formatting.md",
]


def load_shared_instructions() -> str:
  fragments = [
      (INSTRUCTIONS_DIR / name).read_text().strip()
      for name in INSTRUCTION_FRAGMENT_FILES
  ]
  return "\n\n".join(fragments)


def _substitute_shared_instructions(text: str, shared_instructions: str) -> str:
  lines = text.splitlines(keepends=True)
  output_lines = []
  for line in lines:
    stripped = line.rstrip("\n")
    if stripped.strip() == "__SHARED_INSTRUCTIONS__":
      indent = " " * (len(stripped) - len(stripped.lstrip(" ")))
      block = "\n".join(
          f"{indent}{l}" if l else "" for l in shared_instructions.splitlines()
      )
      output_lines.append(block + "\n")
    else:
      output_lines.append(line)
  return "".join(output_lines)


def render_logical_agent(
    domain: str, name: str, display_name: str, domains_root: Path
) -> Path:
  """Generates a new logical agent under domains_root/<domain>/agents/<name>.

  Returns the path to the generated logical agent directory.
  Raises FileExistsError if the target directory already exists.
  """
  target = domains_root / domain / "agents" / name
  if target.exists():
    raise FileExistsError(f"Logical agent already exists at {target}")

  shutil.copytree(
      TEMPLATE_DIR, target, ignore=shutil.ignore_patterns("__pycache__")
  )

  shared_instructions = load_shared_instructions()
  tokens = {
      "__DOMAIN__": domain,
      "__LOGICAL_AGENT__": name,
      "__DISPLAY_NAME__": display_name,
  }

  for path in target.rglob("*"):
    if not path.is_file() or path.suffix.lower() in (".png", ".jpg", ".jpeg", ".ico", ".pyc"):
      continue
    text = path.read_text()
    text = _substitute_shared_instructions(text, shared_instructions)
    for token, value in tokens.items():
      text = text.replace(token, value)
    path.write_text(text)

  return target


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--domain", required=True)
  parser.add_argument(
      "--name", required=True, help="snake_case logical agent folder name"
  )
  parser.add_argument("--display-name", required=True)
  parser.add_argument(
      "--domains-root",
      type=Path,
      default=REPO_ROOT / "domains",
      help="Root directory containing domain folders (default: repo domains/)",
  )
  args = parser.parse_args()

  target = render_logical_agent(
      domain=args.domain,
      name=args.name,
      display_name=args.display_name,
      domains_root=args.domains_root,
  )
  print(f"Created logical agent at {target}")


if __name__ == "__main__":
  main()
