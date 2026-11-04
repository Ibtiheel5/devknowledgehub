import { apiGet, apiPost } from "./api";

export function getAgentCatalog() {
  return apiGet("/api/v1/agents/catalog");
}

export function runSpecialistAgent(repoName, agent, question, maxResults = 10) {
  return apiPost("/api/v1/agents/specialist", {
    repo_name: repoName,
    agent,
    question,
    max_results: maxResults
  });
}

export function searchAgent(repoName, question, maxResults = 10) {
  return apiPost("/api/v1/agents/search", {
    repo_name: repoName,
    question,
    max_results: maxResults
  });
}

export function askAgent(repoName, question, topK = 8) {
  return apiPost("/api/v1/agents/ask", {
    repo_name: repoName,
    question,
    top_k: topK
  });
}
