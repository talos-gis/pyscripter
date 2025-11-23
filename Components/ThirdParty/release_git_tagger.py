import configparser
import subprocess
from collections import defaultdict
from pathlib import Path


def load_ini_sections(ini_file: str, tag: str | None = None) -> dict:
    """
    Loads sections that begin with `tag` from an INI file.
    Returns: { section_name : {key: value, ...} }
    """
    ini_path = Path(ini_file)
    if not ini_path.exists():
        raise FileNotFoundError(f"INI file not found: {ini_file}")

    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(ini_file)
    skip_sections = ["Options"]

    result = {}
    for section in cfg.sections():
        if section in skip_sections:
            continue
        if tag is None or section.startswith(tag):
            # Convert section items to a plain dict
            items = cfg.items(section)
            items = dict(items)
            print(f"{section=} {items}")
            result[section] = items

    return result


def run(cmd, cwd=None):
    """Run a shell command and return trimmed stdout."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def run_cmd(cmd, cwd, dry_run: bool):
    if dry_run:
        print(f"[DRY-RUN] {cmd}")
        return ""
    return run(cmd, cwd)


def tag_release_repos(repos: dict, root_dir: str, tag_name: str, dry_run: bool = False):
    """
    Iterates each repo entry (Name, Git, Folder).
    For each repo:
      - cd into root/Folder
      - detect current branch
      - create & push a *tag* (not a branch)
      - print summary line
      - checkout back to original branch
    If dry_run=True, all git operations are *printed* but NOT executed.
    """
    root_dir = Path(root_dir)

    for section, data in repos.items():
        name = data.get("name")
        git = data.get("git")
        folder = data.get("folder")
        if not name or not git or not folder:
            err = f"{section}: {data} missing input"
            raise Exception(err)

        repo_path = root_dir / folder

        if not repo_path.exists():
            err = f"[SKIP] {name}: folder not found ({repo_path})"
            raise Exception(err)

        # Get current branch
        current_branch = run("git rev-parse --abbrev-ref HEAD", cwd=repo_path)

        print(f"{name}: {git} @ {folder} @ {current_branch}")

        # Git operations
        cmds = [
            f"git tag \"{tag_name}\"",  # create tag
            f"git push origin \"{tag_name}\"",  # push tag
        ]

        for cmd in cmds:
            run_cmd(cmd, cwd=repo_path, dry_run=dry_run)

        # Switch back to original branch (real only)
        # if not dry_run:
        #     run(f"git checkout \"{current_branch}\"", cwd=repo_path)
        # else:
        #     print(f"  [DRY-RUN] git checkout \"{current_branch}\"")


def fast_forward_from_upstream(repos: dict, root_dir: str, *, dry_run: bool = False):
    """
    For each repo:
      - If remote 'upstream' exists:
            * fetch upstream
            * check if current branch can fast-forward to upstream/<branch>
            * if yes -> fast forward merge + push to origin
            * else -> print explanation
      - If remote 'upstream' does not exist → print skip message
    """

    root_dir = Path(root_dir)
    status = defaultdict(list)
    for section, data in repos.items():
        name = data.get("name")
        folder = data.get("folder")

        repo_path = root_dir / folder

        if not repo_path.exists():
            print(f"[SKIP] {name}: folder not found {repo_path}")
            continue

        print(f"\n=== {name} @ {repo_path} ===")

        # Check if 'upstream' exists
        remotes = run_cmd("git remote", repo_path, dry_run=False).splitlines()
        if "upstream" not in remotes:
            print("No upstream remote → skipping.")
            status["no_upstream"].append(repo_path)
            continue

        # Get current branch
        current_branch = run_cmd("git rev-parse --abbrev-ref HEAD", repo_path, dry_run=False)
        if current_branch == "":
            current_branch = "<dry-run-branch>"

        # Fetch upstream

        run_cmd("git fetch upstream", repo_path, dry_run=False)

        # Determine upstream branch name
        upstream_branch = f"upstream/{current_branch}"

        # Ensure upstream branch exists
        upstream_heads = run_cmd("git branch -r", repo_path, dry_run=False)
        if upstream_branch not in upstream_heads:
            print(f"Upstream branch '{upstream_branch}' does not exist.")
            status["no_upstream_branch"].append(repo_path)
            continue

        # Compute merge base
        merge_base = run_cmd(
            f"git merge-base HEAD {upstream_branch}",
            repo_path,
            dry_run=False
        )
        head_commit = run_cmd("git rev-parse HEAD", repo_path, dry_run=False)
        upstream_commit = run_cmd(f"git rev-parse {upstream_branch}", repo_path, dry_run=False)

        # if head_commit == upstream_commit:
        #     print("Fork is already synced. skip.")
        #     continue

        # Logic:
        # If mergebase == HEAD → we can fast-forward
        # If mergebase == upstream → we are ahead (cannot FF)
        # Else → diverged history
        if merge_base == head_commit:
            print("Fast-forward possible → merging upstream into local")

            # Fast forward merge
            run_cmd(f"git merge --ff-only {upstream_branch}", repo_path, dry_run)

            # Push to origin
            run_cmd(f"git push origin {current_branch}", repo_path, dry_run)

            print("✔ Fast-forwarded & pushed to origin.")
            status["Fast-forwarded"].append(repo_path)

        elif merge_base == upstream_commit:
            status["ahead"].append(repo_path)
            print("Local branch is ahead of upstream → cannot fast-forward.")
        else:
            status["diverged"].append(repo_path)
            print("Local and upstream have diverged → manual merge/rebase required.")

    for k, v in status.items():
        print(f"=== Status: {k} ===")
        for r in v:
            print(r)

if __name__ == "__main__":
    dry_run = False
    root_dir = "C:/delphi"
    repos = load_ini_sections("Setup.ini")
    repos["pyscripter"] = {
        "name": "pyscripter",
        "git": "https://github.com/talos-gis/pyscripter",
        "folder": "pyscripter"
    }

    tag_name = "talos_2025.04.10"
    # tag_release_repos(
    #     repos=repos,
    #     root_dir=root_dir,
    #     tag_name=tag_name,
    #     dry_run=dry_run
    # )

    fast_forward_from_upstream(
        repos=repos,
        root_dir=root_dir,
        dry_run=dry_run
    )
