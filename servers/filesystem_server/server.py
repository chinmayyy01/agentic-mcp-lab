from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem-server")

SANDBOX_ROOT = Path(__file__).parent / "sandbox"
SANDBOX_ROOT = SANDBOX_ROOT.resolve()

def _resolve_safe_path(relative_path: str) -> Path:
    """
    Resolves a user supplied relative path against the sandbox root, and raises an error if it tries to escape it.
    """
    candidate = (SANDBOX_ROOT / relative_path).resolve()
    if not str(candidate).startswith(str(SANDBOX_ROOT)):
        raise ValueError(f"Access Denied: '{relative_path}' is outside of the sandbox.")
    return candidate

@mcp.tool()
def list_dir(path: str = '.') -> str:
    """
    Lists files and subdirectories inside the given directory path.
    The path must be relative (e.g. 'projects' or 'projects/subfolder'),
    never an absolute path starting with '/'. Use '.' to list the root
    of the allowed sandbox directory.
    """
    try:
        target = _resolve_safe_path(path)
    except ValueError as e:
        return f"Error: {e}. Please use a relative path within the sandbox."

    if not target.exists():
        return f"Error: path '{path}' does not exist."
    if not target.is_dir():
        return f"Error: '{path}' is a file, not a directory."
    
    entries = []
    for item in sorted(target.iterdir()):
        kind = "DIR" if item.is_dir() else "FILE"
        entries.append(f"{kind}: {item.name}")
    
    if not entries:
        return f"The directory '{path}' is empty."
    
    return "\n".join(entries)

@mcp.tool()
def read_file(path: str) -> str:
    """
    Reads and returns the text content of a file at the given path.
    The path must be relative (e.g. 'notes.txt' or 'projects/app.py'),
    never an absolute path starting with '/'.
    """
    try:
        target = _resolve_safe_path(path)
    except ValueError as e:
        return f"Error: {e}. Please use a relative path within the sandbox."

    if not target.exists():
        return f"Error: file '{path}' does not exist."
    if target.is_dir():
        return f"Error: '{path}' is a directory, not a file."
    
    try:
        return target.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return f"Error: file '{path}' is not a readable text file (binary content)."
    
@mcp.tool()
def write_file(path: str, content: str, overwrite: bool = False) -> str:
    """
    Writes text content to a file at the given path. The path must be
    relative (e.g. 'notes.txt' or 'projects/new.py'), never an absolute
    path starting with '/'. Fails if the file already exists unless
    overwrite=True is explicitly passed.
    """
    try:
        target = _resolve_safe_path(path)
    except ValueError as e:
        return f"Error: {e}. Please use a relative path within the sandbox."

    if target.exists() and not overwrite:
        return f"Error: '{path}' already exists. Pass overwrite=True to replace it."

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} characters to '{path}'."

@mcp.tool()
def search_files(query: str, path: str = ".") -> str:
    """
    Recursively searches for files whose name contains the query string,
    starting from the given directory. The path must be relative
    (e.g. '.' or 'projects'), never an absolute path starting with '/'.
    """
    try:
        target = _resolve_safe_path(path)
    except ValueError as e:
        return f"Error: {e}. Please use a relative path within the sandbox."

    if not target.exists() or not target.is_dir():
        return f"Error: '{path}' is not a valid directory."

    matches = []
    for item in target.rglob("*"):
        if query.lower() in item.name.lower():
            rel_path = item.relative_to(SANDBOX_ROOT)
            kind = "DIR" if item.is_dir() else "FILE"
            matches.append(f"[{kind}] {rel_path}")

    if not matches:
        return f"No files matching '{query}' found under '{path}'."

    return "\n".join(matches)

if __name__ == "__main__":
    mcp.run(transport="stdio")