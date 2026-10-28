from pydantic import BaseModel, Field


class Symbol(BaseModel):
    kind: str  # "class" | "function" | "method"
    name: str
    qualified_name: str
    file: str
    start_line: int
    end_line: int
    parent: str | None = None


class ImportRef(BaseModel):
    file: str
    module: str
    names: list[str] = Field(default_factory=list)
    line: int


class CallRef(BaseModel):
    file: str
    caller: str  # qualified name, ou "<module>"
    callee: str  # texte de l'appel : "foo", "self.bar", "os.path.join"
    line: int


class FileAnalysis(BaseModel):
    path: str
    language: str
    lines: int
    symbols: list[Symbol] = Field(default_factory=list)
    imports: list[ImportRef] = Field(default_factory=list)
    calls: list[CallRef] = Field(default_factory=list)


class RepositoryAnalysis(BaseModel):
    root: str
    languages: dict[str, int]  # langage -> nombre de fichiers
    files: list[FileAnalysis]

    @property
    def symbol_count(self) -> int:
        return sum(len(f.symbols) for f in self.files)
