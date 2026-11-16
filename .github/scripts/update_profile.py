
import json
import urllib.request
from pathlib import Path

USERNAME = "TechParthOps"
README = Path("README.md")
API = "https://api.github.com"

def github_get(endpoint):
    request = urllib.request.Request(
        API + endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "TechParthOps-Profile-Updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def escape(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()

def update_section(content, name, replacement):
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"

    if start not in content or end not in content:
        raise ValueError(f"Missing README markers: {name}")

    before, rest = content.split(start, 1)
    _, after = rest.split(end, 1)

    return f"{before}{start}\n{replacement}\n{end}{after}"

def get_projects():
    repositories = []
    page = 1

    while True:
        batch = github_get(
            f"/users/{USERNAME}/repos"
            f"?type=owner&sort=pushed&direction=desc"
            f"&per_page=100&page={page}"
        )

        if not batch:
            break

        repositories.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    repositories = [
        repo for repo in repositories
        if not repo.get("private")
        and not repo.get("fork")
        and repo["name"].lower() != USERNAME.lower()
    ]

    repositories.sort(
        key=lambda repo: repo.get("pushed_at") or "",
        reverse=True,
    )

    if not repositories:
        return "_No public repositories found._"

    lines = [
        "| Repository | Description | Language |",
        "|---|---|---|",
    ]

    for repo in repositories[:12]:
        name = escape(repo["name"])
        description = escape(
            repo.get("description") or "No description provided."
        )
        language = escape(repo.get("language") or "Not specified")

        lines.append(
            f"| [{name}]({repo['html_url']}) "
            f"| {description} | {language} |"
        )

    print(f"Found {len(repositories)} public repositories.")
    return "\n".join(lines)

def get_activity():
    try:
        events = github_get(
            f"/users/{USERNAME}/events/public?per_page=100"
        )
    except Exception as error:
        print(f"Activity unavailable: {error}")
        return "_Recent public activity is temporarily unavailable._"

    lines = []
    seen = set()

    for event in events:
        if event.get("type") != "PushEvent":
            continue

        repo = event.get("repo", {}).get("name", "")

        for commit in reversed(
            event.get("payload", {}).get("commits", [])
        ):
            sha = commit.get("sha", "")

            if not sha or (repo, sha) in seen:
                continue

            seen.add((repo, sha))

            message = escape(
                commit.get("message", "").splitlines()[0]
            )

            lines.append(
                f"- **[{repo}](https://github.com/{repo})** "
                f"`{sha[:7]}` — {message} "
                f"([commit](https://github.com/{repo}/commit/{sha}))"
            )

            if len(lines) >= 8:
                break

        if len(lines) >= 8:
            break

    return "\n".join(lines) if lines else (
        "_No recent public push activity available._"
    )

def main():
    if not README.exists():
        raise FileNotFoundError("README.md not found")

    content = README.read_text(encoding="utf-8")

    projects = get_projects()
    activity = get_activity()

    content = update_section(content, "PROJECTS", projects)
    content = update_section(content, "ACTIVITY", activity)

    README.write_text(content, encoding="utf-8")

    print("GitHub profile successfully updated.")

if __name__ == "__main__":
    main()
