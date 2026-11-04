import { apiGet, apiPost, apiUpload } from "./api";

function projectBase(name) {
  return `/api/v1/projects/${encodeURIComponent(name)}`;
}

function encodePath(path) {
  return path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

export function listProjects() {
  return apiGet("/api/v1/projects");
}

export function createProject(name, gitUrl, sourceType = "git") {
  return apiPost("/api/v1/projects", {
    name,
    git_url: gitUrl,
    source_type: sourceType
  });
}

export function getProject(name) {
  return apiGet(projectBase(name));
}

export function getProjectStatus(name) {
  return apiGet(`${projectBase(name)}/status`);
}

export function ingestProject(name, gitUrl) {
  return apiPost(`${projectBase(name)}/ingest`, { git_url: gitUrl });
}

export function ingestProjectZip(name, file) {
  return apiUpload(`${projectBase(name)}/ingest/zip`, file);
}

export function getProjectIssues(name) {
  return apiGet(`${projectBase(name)}/issues`);
}

export function createProjectIssue(name, issue) {
  return apiPost(`${projectBase(name)}/issues`, issue);
}

export function getProjectDocuments(name, includeContent = false) {
  return apiGet(`${projectBase(name)}/documents?include_content=${includeContent}`);
}

export function getProjectDocument(name, path) {
  return apiGet(`${projectBase(name)}/documents/${encodePath(path)}`);
}

export function getProjectFindings(name, modelName, limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (modelName) params.set("model_name", modelName);
  return apiGet(`${projectBase(name)}/findings?${params.toString()}`);
}

export function getProjectArchitecture(name) {
  return apiGet(`${projectBase(name)}/architecture`);
}

export function getProjectGraph(name) {
  return apiGet(`${projectBase(name)}/graph`);
}
