import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import styles from "./ForceGraph.module.css";

const DEFAULT_W = 900;
const DEFAULT_H = 520;
const MIN_ZOOM = 0.35;
const MAX_ZOOM = 3;
const LIMIT_OPTIONS = [25, 40, 60, 100, 0];

export const KIND_COLORS = {
  class: "#8f4f3a",
  method: "#b07a5e",
  function: "#6f5a4a",
  field: "#c9a27e",
  default: "#9b8b82"
};

const KIND_LABELS = {
  class: "Classe",
  method: "Méthode",
  function: "Fonction",
  field: "Champ",
  default: "Autre"
};

const colorOf = (kind) => KIND_COLORS[kind] || KIND_COLORS.default;
const labelOf = (kind) => KIND_LABELS[kind] || KIND_LABELS.default;
const shortName = (id) => String(id).split(".").slice(-1)[0];
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const radiusOf = (node) => 7 + Math.min(node?.degree || 0, 14) * 1.15;

const groupOf = (node) => {
  if (node.file) {
    const parts = String(node.file).split("/");
    parts.pop();
    return parts.join("/") || String(node.file);
  }
  const parts = String(node.id).split(".");
  parts.pop();
  return parts.join(".") || "racine";
};

export function buildGraph(calls, symbols = []) {
  const nodes = new Map();
  const links = new Map();
  const add = (id, kind, file) => {
    if (!id) return null;
    if (!nodes.has(id)) {
      nodes.set(id, { id, kind, file: file || null, degree: 0 });
    } else {
      const node = nodes.get(id);
      if (kind && !node.kind) node.kind = kind;
      if (file && !node.file) node.file = file;
    }
    return nodes.get(id);
  };
  for (const c of calls || []) {
    const a = add(c.caller, c.caller_kind, c.caller_file);
    const b = add(c.callee, c.callee_kind, c.callee_file);
    if (!a || !b || a === b) continue;
    const key = `${c.caller}→${c.callee}`;
    if (links.has(key)) continue;
    links.set(key, { source: c.caller, target: c.callee });
    a.degree += 1;
    b.degree += 1;
  }
  for (const s of symbols || []) {
    const id = s.qualified_name ?? s.name;
    if (!id) continue;
    const node = add(id, s.kind, s.file);
    if (node && Number.isFinite(s.degree)) {
      node.trueDegree = Math.max(node.trueDegree || 0, s.degree);
    }
  }
  for (const node of nodes.values()) {
    node.group = groupOf(node);
    node.trueDegree = Math.max(node.trueDegree || 0, node.degree);
  }
  return { nodes: [...nodes.values()], links: [...links.values()] };
}

function subsetGraph(full, limit) {
  if (!limit || full.nodes.length <= limit) return full;
  const score = (node) => node.trueDegree ?? node.degree;
  const ranked = [...full.nodes].sort(
    (a, b) =>
      (b.degree > 0 ? 1 : 0) - (a.degree > 0 ? 1 : 0) ||
      score(b) - score(a) ||
      a.id.localeCompare(b.id)
  );
  const keep = new Set(ranked.slice(0, limit).map((node) => node.id));
  return {
    nodes: full.nodes.filter((node) => keep.has(node.id)),
    links: full.links.filter((link) => keep.has(link.source) && keep.has(link.target))
  };
}

export function ForceGraph({ calls, symbols, selected, onSelect, compact = false }) {
  const fullGraph = useMemo(() => buildGraph(calls, symbols), [calls, symbols]);
  const [limit, setLimit] = useState(compact ? 25 : 60);
  const effectiveLimit = fullGraph.nodes.length > limit && limit > 0 ? limit : 0;
  const graph = useMemo(
    () => subsetGraph(fullGraph, effectiveLimit),
    [fullGraph, effectiveLimit]
  );
  const hasNodes = graph.nodes.length > 0;
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const arrowActive = `arrow-active-${uid}`;

  const wrapRef = useRef(null);
  const svgRef = useRef(null);
  const pos = useRef(new Map());
  const drag = useRef(null);
  const sizeRef = useRef({ w: DEFAULT_W, h: DEFAULT_H });
  const fitRef = useRef(() => {});
  const relaxRef = useRef(() => {});
  const [size, setSize] = useState({ w: DEFAULT_W, h: DEFAULT_H });
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [hover, setHover] = useState(null);
  const [, setFrame] = useState(0);

  const nodeById = useMemo(
    () => new Map(graph.nodes.map((node) => [node.id, node])),
    [graph]
  );

  const linkKeys = useMemo(
    () => new Set(graph.links.map((link) => `${link.source}→${link.target}`)),
    [graph]
  );

  const limitOptions = useMemo(() => {
    const values = LIMIT_OPTIONS.filter(
      (value) => value === 0 || value < fullGraph.nodes.length
    );
    return values.length ? values : [0];
  }, [fullGraph.nodes.length]);

  const active = hover || selected;

  const neighbors = useMemo(() => {
    const set = new Set();
    if (!active) return set;
    set.add(active);
    for (const link of graph.links) {
      if (link.source === active) set.add(link.target);
      if (link.target === active) set.add(link.source);
    }
    return set;
  }, [graph, active]);

  const labeled = useMemo(() => {
    if (graph.nodes.length <= 80) return new Set(graph.nodes.map((node) => node.id));
    return new Set(
      [...graph.nodes]
        .sort((a, b) => (b.trueDegree ?? b.degree) - (a.trueDegree ?? a.degree))
        .slice(0, 50)
        .map((node) => node.id)
    );
  }, [graph]);

  const kinds = useMemo(() => {
    const counts = new Map();
    for (const node of graph.nodes) {
      const kind = node.kind && KIND_COLORS[node.kind] ? node.kind : "default";
      counts.set(kind, (counts.get(kind) || 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [graph]);

  const relax = useCallback(
    (steps, alphaStart) => {
      const { nodes, links } = graph;
      const P = pos.current;
      if (!nodes.length) return;
      const { w, h } = sizeRef.current;
      const scale = Math.sqrt((w * h) / (DEFAULT_W * DEFAULT_H));
      const radii = new Map(nodes.map((node) => [node.id, radiusOf(node)]));
      let alpha = alphaStart;

      for (let step = 0; step < steps; step += 1) {
        for (let i = 0; i < nodes.length; i += 1) {
          const p = P.get(nodes[i].id);
          if (!p) continue;
          for (let j = i + 1; j < nodes.length; j += 1) {
            const q = P.get(nodes[j].id);
            if (!q) continue;
            let dx = p.x - q.x;
            let dy = p.y - q.y;
            let d2 = dx * dx + dy * dy;
            if (d2 < 0.01) {
              dx = (i - j) || 0.5;
              dy = (j - i) || 0.5;
              d2 = dx * dx + dy * dy;
            }
            const d = Math.sqrt(d2);
            const minDistance =
              (radii.get(nodes[i].id) + radii.get(nodes[j].id) + 16) * scale;
            if (d < minDistance) {
              const push = ((minDistance - d) / d) * 0.5;
              p.vx += dx * push;
              p.vy += dy * push;
              q.vx -= dx * push;
              q.vy -= dy * push;
            }
            const repulsion = ((4200 * scale) / Math.max(d2, 160)) * alpha;
            const fx = (dx / d) * repulsion;
            const fy = (dy / d) * repulsion;
            p.vx += fx;
            p.vy += fy;
            q.vx -= fx;
            q.vy -= fy;
            if (nodes[i].group === nodes[j].group && d > 110 * scale) {
              const pull = (d - 110 * scale) * 0.025 * alpha;
              const gx = (dx / d) * pull;
              const gy = (dy / d) * pull;
              p.vx -= gx;
              p.vy -= gy;
              q.vx += gx;
              q.vy += gy;
            }
          }
        }

        for (const link of links) {
          const p = P.get(link.source);
          const q = P.get(link.target);
          if (!p || !q) continue;
          const dx = q.x - p.x;
          const dy = q.y - p.y;
          const d = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const ideal = (150 + (radii.get(link.source) + radii.get(link.target)) * 0.6) * scale;
          const force = (d - ideal) * 0.03 * alpha;
          const fx = (dx / d) * force;
          const fy = (dy / d) * force;
          p.vx += fx;
          p.vy += fy;
          q.vx -= fx;
          q.vy -= fy;
        }

        const cx = w / 2;
        const cy = h / 2;
        for (const node of nodes) {
          const p = P.get(node.id);
          if (!p) continue;
          p.vx += (cx - p.x) * 0.008 * alpha;
          p.vy += (cy - p.y) * 0.008 * alpha;
          p.vx *= 0.85;
          p.vy *= 0.85;
          const maxSpeed = 36 * scale;
          p.vx = clamp(p.vx, -maxSpeed, maxSpeed);
          p.vy = clamp(p.vy, -maxSpeed, maxSpeed);
          p.x = clamp(p.x + p.vx, 24, w - 24);
          p.y = clamp(p.y + p.vy, 24, h - 24);
        }

        alpha *= 0.965;
      }
    },
    [graph]
  );

  const fitToView = useCallback(() => {
    const { nodes } = graph;
    const P = pos.current;
    if (!nodes.length) return;
    const { w, h } = sizeRef.current;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const node of nodes) {
      const p = P.get(node.id);
      if (!p) continue;
      const r = radiusOf(node) + 20;
      minX = Math.min(minX, p.x - r);
      minY = Math.min(minY, p.y - r);
      maxX = Math.max(maxX, p.x + r);
      maxY = Math.max(maxY, p.y + r);
    }
    if (!Number.isFinite(minX)) return;
    const bw = Math.max(maxX - minX, 1);
    const bh = Math.max(maxY - minY, 1);
    const pad = 24;
    const k = clamp(Math.min((w - pad * 2) / bw, (h - pad * 2) / bh), 0.55, 1.8);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    setView({ k, x: w / 2 - cx * k, y: h / 2 - cy * k });
  }, [graph]);

  useEffect(() => {
    relaxRef.current = relax;
  }, [relax]);

  useEffect(() => {
    fitRef.current = fitToView;
  }, [fitToView]);

  useEffect(() => {
    const { nodes } = graph;
    const P = new Map();
    if (!nodes.length) {
      pos.current = P;
      setFrame((frame) => frame + 1);
      return;
    }
    const { w, h } = sizeRef.current;
    const golden = Math.PI * (3 - Math.sqrt(5));
    const maxRadius = Math.min(w, h) * 0.42;
    nodes.forEach((node, index) => {
      const radius = nodes.length > 1 ? Math.sqrt((index + 0.5) / nodes.length) * maxRadius : 0;
      const angle = index * golden;
      P.set(node.id, {
        x: w / 2 + Math.cos(angle) * radius,
        y: h / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0
      });
    });
    pos.current = P;
    relaxRef.current(240, 1);
    setFrame((frame) => frame + 1);
    fitRef.current();
  }, [graph]);

  useEffect(() => {
    const element = wrapRef.current;
    if (!element) return undefined;
    const apply = () => {
      const w = Math.max(320, Math.round(element.clientWidth) || DEFAULT_W);
      const h = Math.max(220, Math.round(element.clientHeight) || DEFAULT_H);
      if (w === sizeRef.current.w && h === sizeRef.current.h) return;
      sizeRef.current = { w, h };
      setSize({ w, h });
      for (const p of pos.current.values()) {
        p.x = clamp(p.x, 24, w - 24);
        p.y = clamp(p.y, 24, h - 24);
      }
      if (pos.current.size) {
        relaxRef.current(70, 0.25);
        fitRef.current();
      }
      setFrame((frame) => frame + 1);
    };
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasNodes]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return undefined;
    const onWheel = (event) => {
      event.preventDefault();
      const rect = svg.getBoundingClientRect();
      const px = ((event.clientX - rect.left) / rect.width) * sizeRef.current.w;
      const py = ((event.clientY - rect.top) / rect.height) * sizeRef.current.h;
      const factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
      setView((current) => {
        const k = clamp(current.k * factor, MIN_ZOOM, MAX_ZOOM);
        const ratio = k / current.k;
        return {
          k,
          x: px - (px - current.x) * ratio,
          y: py - (py - current.y) * ratio
        };
      });
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [hasNodes]);

  const toGraphCoords = (event) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0, rawX: 0, rawY: 0 };
    const matrix = svg.getScreenCTM()?.inverse();
    if (!matrix) return { x: 0, y: 0, rawX: 0, rawY: 0 };
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const p = point.matrixTransform(matrix);
    return {
      x: (p.x - view.x) / view.k,
      y: (p.y - view.y) / view.k,
      rawX: p.x,
      rawY: p.y
    };
  };

  const onNodeDown = (event, id) => {
    event.stopPropagation();
    event.preventDefault();
    svgRef.current?.setPointerCapture?.(event.pointerId);
    const coords = toGraphCoords(event);
    drag.current = {
      type: "node",
      id,
      startX: coords.rawX,
      startY: coords.rawY,
      moved: false
    };
  };

  const onBgDown = (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    const coords = toGraphCoords(event);
    drag.current = {
      type: "pan",
      startX: coords.rawX,
      startY: coords.rawY,
      viewX: view.x,
      viewY: view.y,
      moved: false
    };
    svgRef.current?.setPointerCapture?.(event.pointerId);
  };

  const onMove = (event) => {
    const current = drag.current;
    if (!current) return;
    const coords = toGraphCoords(event);
    if (current.type === "node") {
      if (Math.hypot(coords.rawX - current.startX, coords.rawY - current.startY) > 3) {
        current.moved = true;
      }
      const p = pos.current.get(current.id);
      if (p) {
        p.x = coords.x;
        p.y = coords.y;
        p.vx = 0;
        p.vy = 0;
      }
      setFrame((frame) => frame + 1);
    } else {
      if (Math.hypot(coords.rawX - current.startX, coords.rawY - current.startY) > 2) {
        current.moved = true;
      }
      setView((value) => ({
        ...value,
        x: current.viewX + (coords.rawX - current.startX),
        y: current.viewY + (coords.rawY - current.startY)
      }));
    }
  };

  const onUp = (event) => {
    const current = drag.current;
    drag.current = null;
    if (svgRef.current?.hasPointerCapture?.(event.pointerId)) {
      svgRef.current.releasePointerCapture(event.pointerId);
    }
    if (!current) return;
    if (current.type === "node") {
      if (!current.moved) onSelect?.(current.id === selected ? null : current.id);
      else {
        relaxRef.current(90, 0.28);
        setFrame((frame) => frame + 1);
      }
    } else if (!current.moved) {
      onSelect?.(null);
    }
  };

  const zoom = (factor) =>
    setView((current) => {
      const k = clamp(current.k * factor, MIN_ZOOM, MAX_ZOOM);
      const ratio = k / current.k;
      const { w, h } = sizeRef.current;
      return {
        k,
        x: w / 2 - (w / 2 - current.x) * ratio,
        y: h / 2 - (h / 2 - current.y) * ratio
      };
    });

  if (!hasNodes) return null;

  const { w, h } = size;
  const labelSize = 11 / view.k;
  const labelOffset = 12 / view.k;
  const labelStroke = 3 / view.k;

  return (
    <div ref={wrapRef} className={`${styles.wrap} ${compact ? styles.compact : ""}`}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${w} ${h}`}
        className={styles.svg}
        onPointerDown={onBgDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        role="img"
        aria-label={`Graphe de connaissances : ${graph.nodes.length} nœuds et ${graph.links.length} relations`}
      >
        <defs>
          <marker
            id={arrowActive}
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M0,0 L8,4 L0,8 z" fill="#b9684b" />
          </marker>
        </defs>

        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {graph.links.map((link) => {
            const p = pos.current.get(link.source);
            const q = pos.current.get(link.target);
            if (!p || !q) return null;
            const isActive = Boolean(active) && (link.source === active || link.target === active);
            const dim = Boolean(active) && !isActive;
            const sourceRadius = radiusOf(nodeById.get(link.source)) + 2;
            const targetRadius = radiusOf(nodeById.get(link.target)) + 5;
            const dx = q.x - p.x;
            const dy = q.y - p.y;
            const distance = Math.max(Math.hypot(dx, dy), 1);
            const ux = dx / distance;
            const uy = dy / distance;
            const sx = p.x + ux * sourceRadius;
            const sy = p.y + uy * sourceRadius;
            const tx = q.x - ux * targetRadius;
            const ty = q.y - uy * targetRadius;
            const curved = linkKeys.has(`${link.target}→${link.source}`);
            const offset = curved ? 16 : 0;
            const cx = (sx + tx) / 2 - uy * offset;
            const cy = (sy + ty) / 2 + ux * offset;
            return (
              <path
                key={`${link.source}-${link.target}`}
                d={`M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`}
                className={`${styles.link} ${isActive ? styles.linkActive : ""} ${
                  dim ? styles.dim : ""
                }`}
                markerEnd={isActive ? `url(#${arrowActive})` : undefined}
              />
            );
          })}

          {graph.nodes.map((node) => {
            const p = pos.current.get(node.id);
            if (!p) return null;
            const radius = radiusOf(node);
            const isActive = node.id === active;
            const isNeighbor = neighbors.has(node.id);
            const dim = Boolean(active) && !isNeighbor;
            const showLabel = active ? isActive || isNeighbor : labeled.has(node.id);
            const name = shortName(node.id);
            const label = name.length > 22 ? `${name.slice(0, 21)}…` : name;
            return (
              <g
                key={node.id}
                transform={`translate(${p.x} ${p.y})`}
                className={`${styles.node} ${dim ? styles.dim : ""} ${
                  isActive ? styles.active : ""
                }`}
                onPointerDown={(event) => onNodeDown(event, node.id)}
                onPointerEnter={() => setHover(node.id)}
                onPointerLeave={() => setHover((value) => (value === node.id ? null : value))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect?.(node.id === selected ? null : node.id);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-label={node.id}
              >
                {node.degree === 0 && <circle r={radius + 2.5} className={styles.isolatedRing} />}
                {isActive && <circle r={radius + 7} className={styles.halo} />}
                <circle r={radius} fill={colorOf(node.kind)} className={styles.dot} />
                <circle r={Math.max(radius - 3.2, 1.6)} className={styles.dotInner} />
                {showLabel && (
                  <text
                    y={radius + labelOffset}
                    textAnchor="middle"
                    className={styles.label}
                    style={{ fontSize: `${labelSize}px`, strokeWidth: `${labelStroke}px` }}
                  >
                    {label}
                  </text>
                )}
                <title>{node.id}</title>
              </g>
            );
          })}
        </g>
      </svg>

      <div className={styles.toolbar}>
        <span className={styles.stats}>
          {graph.nodes.length}
          {effectiveLimit ? ` / ${fullGraph.nodes.length}` : ""} nœuds · {graph.links.length}{" "}
          liens
        </span>
        <label className={styles.limit}>
          <span>Afficher</span>
          <select
            value={effectiveLimit}
            onChange={(event) => setLimit(Number(event.target.value))}
            aria-label="Nombre de nœuds affichés"
          >
            {limitOptions.map((value) => (
              <option key={value} value={value}>
                {value === 0 ? `Tout (${fullGraph.nodes.length})` : value}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className={styles.controls}>
        <button type="button" onClick={() => zoom(1.2)} aria-label="Zoom avant" title="Zoom avant">
          +
        </button>
        <button
          type="button"
          onClick={() => zoom(1 / 1.2)}
          aria-label="Zoom arrière"
          title="Zoom arrière"
        >
          −
        </button>
        <button
          type="button"
          onClick={() => fitRef.current()}
          aria-label="Ajuster à la vue"
          title="Ajuster à la vue"
        >
          ⛶
        </button>
        <button
          type="button"
          onClick={() => setView({ x: 0, y: 0, k: 1 })}
          aria-label="Recentrer"
          title="Recentrer"
        >
          ⟲
        </button>
      </div>

      <div className={styles.legend}>
        {kinds.map(([kind, count]) => (
          <span key={kind}>
            <i style={{ background: colorOf(kind) }} />
            {labelOf(kind)} <b>{count}</b>
          </span>
        ))}
      </div>

      <div className={styles.hint}>Molette pour zoomer · glisser pour déplacer</div>
    </div>
  );
}
