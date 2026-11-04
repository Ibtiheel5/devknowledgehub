"""Détection best-effort des technologies d'un dépôt (langages, frameworks, outillage)."""
import json
from pathlib import Path

from app.schemas.code import RepositoryAnalysis

MAX_READ_BYTES = 512_000

_JS_DEPS = {
    "react": ("React", "framework"),
    "next": ("Next.js", "framework"),
    "vue": ("Vue", "framework"),
    "nuxt": ("Nuxt", "framework"),
    "@angular/core": ("Angular", "framework"),
    "svelte": ("Svelte", "framework"),
    "express": ("Express", "framework"),
    "nestjs": ("NestJS", "framework"),
    "vite": ("Vite", "build"),
    "webpack": ("Webpack", "build"),
    "typescript": ("TypeScript", "language"),
    "jest": ("Jest", "testing"),
    "vitest": ("Vitest", "testing"),
    "tailwindcss": ("Tailwind CSS", "ui"),
    "axios": ("Axios", "http"),
    "redux": ("Redux", "state"),
    "@tanstack/react-query": ("React Query", "state"),
    "prisma": ("Prisma", "database"),
}

_PY_DEPS = {
    "fastapi": ("FastAPI", "framework"),
    "django": ("Django", "framework"),
    "flask": ("Flask", "framework"),
    "sqlalchemy": ("SQLAlchemy", "orm"),
    "pydantic": ("Pydantic", "validation"),
    "pandas": ("pandas", "data"),
    "numpy": ("NumPy", "data"),
    "scikit-learn": ("scikit-learn", "ml"),
    "sklearn": ("scikit-learn", "ml"),
    "torch": ("PyTorch", "ml"),
    "tensorflow": ("TensorFlow", "ml"),
    "transformers": ("Hugging Face Transformers", "ml"),
    "pytest": ("pytest", "testing"),
    "uvicorn": ("Uvicorn", "runtime"),
    "celery": ("Celery", "jobs"),
    "psycopg": ("psycopg", "database"),
    "neo4j": ("Neo4j", "database"),
}

_JAVA_DEPS = {
    "spring-boot": ("Spring Boot", "framework"),
    "spring-web": ("Spring Web", "framework"),
    "hibernate": ("Hibernate", "orm"),
    "junit": ("JUnit", "testing"),
    "maven": ("Maven", "build"),
    "gradle": ("Gradle", "build"),
}

_LANGUAGE_NAMES = {
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "tsx": "TSX",
}

_JSON_FILES = ("package.json",)
_PY_FILES = ("requirements.txt", "requirements-ml.txt", "pyproject.toml", "Pipfile", "setup.py")
_JAVA_FILES = ("pom.xml", "build.gradle", "build.gradle.kts")


def _read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_READ_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_files(root: Path, names: tuple[str, ...], max_depth: int = 3) -> list[Path]:
    found: list[Path] = []
    for name in names:
        found += [p for p in root.glob(name) if p.is_file()]
        found += [p for p in root.glob(f"*/{name}") if p.is_file()]
        if max_depth >= 3:
            found += [p for p in root.glob(f"*/*/{name}") if p.is_file()]
    return list(dict.fromkeys(found))


def detect_technologies(root: Path, analysis: RepositoryAnalysis) -> dict:
    technologies: dict[str, dict] = {}

    def add(name: str, category: str, version: str | None = None) -> None:
        key = name.lower()
        if key not in technologies:
            technologies[key] = {"name": name, "category": category, "version": version}
        elif version and not technologies[key]["version"]:
            technologies[key]["version"] = version

    for language in analysis.languages:
        add(_LANGUAGE_NAMES.get(language, language.title()), "language")

    for package_file in _find_files(root, _JSON_FILES):
        try:
            data = json.loads(_read(package_file) or "{}")
        except json.JSONDecodeError:
            continue
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        add("npm", "build")
        for dep, version in deps.items():
            if dep in _JS_DEPS:
                name, category = _JS_DEPS[dep]
                add(name, category, version)
        if data.get("scripts", {}).get("build"):
            add("npm scripts", "build")

    python_text = "\n".join(_read(p).lower() for p in _find_files(root, _PY_FILES))
    for dep, (name, category) in _PY_DEPS.items():
        if dep in python_text:
            add(name, category)

    java_text = "\n".join(_read(p).lower() for p in _find_files(root, _JAVA_FILES))
    for dep, (name, category) in _JAVA_DEPS.items():
        if dep in java_text:
            add(name, category)

    infra_text = "\n".join(
        _read(p).lower()
        for p in [
            *_find_files(root, ("Dockerfile", "docker-compose.yml", "docker-compose.yaml")),
            *_find_files(root, (".env.example", "docker-compose.prod.yml")),
        ]
    )
    if "dockerfile" in {p.name.lower() for p in _find_files(root, ("Dockerfile",))} or infra_text:
        add("Docker", "runtime")
    if "kind: deployment" in infra_text or "kubectl" in infra_text:
        add("Kubernetes", "runtime")
    for marker, names in (
        ("postgres", ("PostgreSQL",)),
        ("pgvector", ("PostgreSQL", "pgvector")),
        ("neo4j", ("Neo4j",)),
        ("redis", ("Redis",)),
        ("mongodb", ("MongoDB",)),
        ("mysql", ("MySQL",)),
    ):
        if marker in infra_text:
            for name in names:
                add(name, "database")

    if (root / ".github" / "workflows").is_dir():
        add("GitHub Actions", "ci")

    names = {t["name"] for t in technologies.values()}
    if {"React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt"} & names and {
        "FastAPI",
        "Django",
        "Flask",
        "Spring Boot",
        "Express",
        "NestJS",
    } & names:
        project_type = "full-stack"
    elif "Docker" in names:
        project_type = "service"
    elif _find_files(root, ("pyproject.toml", "setup.py")):
        project_type = "library"
    else:
        project_type = "application"

    return {
        "technologies": sorted(technologies.values(), key=lambda t: t["name"].lower()),
        "frameworks": sorted(
            t["name"] for t in technologies.values() if t["category"] == "framework"
        ),
        "project_type": project_type,
    }
