import { apiPost } from "./api";

export function indexRepository(repoName, gitUrl) {
  return apiPost("/api/v1/rag/index", {
    repo_name: repoName,
    git_url: gitUrl
  });
}
