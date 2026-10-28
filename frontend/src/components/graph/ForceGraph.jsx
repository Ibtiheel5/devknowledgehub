import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "./ForceGraph.module.css";

const W = 900;
const H = 520;

export const KIND_COLORS = {
  class: "#6d5bb8",
  method: "#15794f",
  function: "#2f6f9e",
  default: "#77857d"
};

const colorOf = (kind) => KIND_COLORS[kind] || KIND_COLORS.default;
const shortName = (id) => id.split(".").slice(-1)[0];

export function buildGraph(calls) {
  const nodes = new Map();
  const links = new Map();
  const add = (id, kind) => {
    if (!id) return null;
    if (!nodes.has(id)) nodes.set(id, { id, kind, degree: 0 });
    else if (kind && !nodes.get(id).kind) nodes.get(id).kind = kind;
    return nodes.get(id);
  };
  for (const c of calls) {
    const a = add(c.caller, c.caller_kind);
    const b = add(c.callee, c.callee_kind);
    if (!a || !b || a === b) continue;
    const key = `${c.caller}→${c.callee}`;
    if (links.has(key)) continue;
    links.set(key, { source: c.caller, target: c.callee });
    a.degree += 1;
    b.degree += 1;
  }
  return { nodes: [...nodes.values()], links: [...links.values()] };
}

export function ForceGraph({ calls, selected, onSelect }) {
  const graph = useMemo(() => buildGraph(calls), [calls]);
  const pos = useRef(new Map());
  const alpha = useRef(1);
  const raf = useRef(0);
  const svgRef = useRef(null);
  const drag = useRef(null);
  const [, setFrame] = useState(0);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });

  const neighbors = useMemo(() => {
    const set = new Set();
    if (!selected) return set;
    set.add(selected);
    for (const l of graph.links) {
      if (l.source === selected) set.add(l.target);
      if (l.target === selected) set.add(l.source);
    }
    return set;
  }, [graph, selected]);

  const loop = useCallback(() => {
    const { nodes, links } = graph;
    const P = pos.current;
    const a = alpha.current;
    if (a < 0.02) {
      raf.current = 0;
      return;
    }
    for (let i = 0; i < nodes.length; i++) {
      const p = P.get(nodes[i].id);
      for (let j = i + 1; j < nodes.length; j++) {
        const q = P.get(nodes[j].id);
        let dx = p.x - q.x;
        let dy = p.y - q.y;
        const d2 = Math.max(dx * dx + dy * dy, 25);
        const f = (2600 / d2) * a;
        const d = Math.sqrt(d2);
        dx = (dx / d) * f;
        dy = (dy / d) * f;
        p.vx += dx; p.vy += dy; q.vx -= dx; q.vy -= dy;
      }
    }
    for (const l of links) {
      const p = P.get(l.source);
      const q = P.get(l.target);
      const dx = q.x - p.x;
      const dy = q.y - p.y;
      const d = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const f = (d - 80) * 0.04 * a;
      const fx = (dx / d) * f;
      const fy = (dy / d) * f;
      p.vx += fx; p.vy += fy; q.vx -= fx; q.vy -= fy;
    }
    for (const n of nodes) {
      const p = P.get(n.id);
      p.vx += (W / 2 - p.x) * 0.012 * a;
      p.vy += (H / 2 - p.y) * 0.012 * a;
      if (p.fixed) { p.vx = 0; p.vy = 0; continue; }
      p.vx *= 0.82; p.vy *= 0.82;
      p.x = Math.min(W - 20, Math.max(20, p.x + p.vx));
      p.y = Math.min(H - 20, Math.max(20, p.y + p.vy));
    }
    alpha.current *= 0.985;
    setFrame((f) => f + 1);
    raf.current = requestAnimationFrame(loop);
  }, [graph]);

  const reheat = useCallback(() => {
    alpha.current = Math.max(alpha.current, 0.4);
    if (!raf.current) raf.current = requestAnimationFrame(loop);
  }, [loop]);

  useEffect(() => {
    const P = new Map();
    const n = graph.nodes.length;
    graph.nodes.forEach((node, i) => {
      const angle = (i / Math.max(n, 1)) * Math.PI * 2;
      const r = 80 + (i % 7) * 30;
      P.set(node.id, { x: W / 2 + Math.cos(angle) * r, y: H / 2 + Math.sin(angle) * r, vx: 0, vy: 0 });
    });
    pos.current = P;
    alpha.current = 1;
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf.current);
      raf.current = 0;
    };
  }, [graph, loop]);

  const toGraphCoords = (e) => {
    const svg = svgRef.current;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const m = svg.getScreenCTM().inverse();
    const p = pt.matrixTransform(m);
    return { x: (p.x - view.x) / view.k, y: (p.y - view.y) / view.k, rawX: p.x, rawY: p.y };
  };

  const onNodeDown = (e, id) => {
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    const c = toGraphCoords(e);
    drag.current = { type: "node", id, startX: c.rawX, startY: c.rawY, moved: false };
    pos.current.get(id).fixed = true;
  };

  const onBgDown = (e) => {
    const c = toGraphCoords(e);
    drag.current = { type: "pan", startX: c.rawX, startY: c.rawY, vx: view.x, vy: view.y };
  };

  const onMove = (e) => {
    const d = drag.current;
    if (!d) return;
    const c = toGraphCoords(e);
    if (d.type === "node") {
      if (Math.hypot(c.rawX - d.startX, c.rawY - d.startY) > 3) d.moved = true;
      const p = pos.current.get(d.id);
      p.x = c.x; p.y = c.y;
      reheat();
    } else {
      setView((v) => ({ ...v, x: d.vx + (c.rawX - d.startX), y: d.vy + (c.rawY - d.startY) }));
    }
  };

  const onUp = () => {
    const d = drag.current;
    drag.current = null;
    if (d?.type === "node") {
      pos.current.get(d.id).fixed = false;
      if (!d.moved) onSelect?.(d.id === selected ? null : d.id);
    } else if (d?.type === "pan") {
      /* rien */
    }
  };

  const zoom = (factor) =>
    setView((v) => {
      const k = Math.min(3, Math.max(0.4, v.k * factor));
      const r = k / v.k;
      return { k, x: W / 2 - (W / 2 - v.x) * r, y: H / 2 - (H / 2 - v.y) * r };
    });

  if (graph.nodes.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className={styles.svg}
        onPointerDown={onBgDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerLeave={onUp}
      >
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {graph.links.map((l) => {
            const p = pos.current.get(l.source);
            const q = pos.current.get(l.target);
            if (!p || !q) return null;
            const active = selected && (l.source === selected || l.target === selected);
            const dim = selected && !active;
            return (
              <line
                key={`${l.source}-${l.target}`}
                x1={p.x} y1={p.y} x2={q.x} y2={q.y}
                className={`${styles.link} ${active ? styles.linkActive : ""} ${dim ? styles.dim : ""}`}
              />
            );
          })}
          {graph.nodes.map((n) => {
            const p = pos.current.get(n.id);
            if (!p) return null;
            const r = 6 + Math.min(n.degree, 12) * 1.1;
            const dim = selected && !neighbors.has(n.id);
            const showLabel = n.id === selected || neighbors.has(n.id) || n.degree >= 4;
            return (
              <g
                key={n.id}
                transform={`translate(${p.x} ${p.y})`}
                className={`${styles.node} ${dim ? styles.dim : ""}`}
                onPointerDown={(e) => onNodeDown(e, n.id)}
              >
                <circle
                  r={r}
                  fill={colorOf(n.kind)}
                  className={n.id === selected ? styles.selected : ""}
                />
                {showLabel && (
                  <text y={-r - 5} textAnchor="middle" className={styles.label}>
                    {shortName(n.id)}
                  </text>
                )}
                <title>{n.id}</title>
              </g>
            );
          })}
        </g>
      </svg>
      <div className={styles.controls}>
        <button type="button" onClick={() => zoom(1.2)} aria-label="Zoom avant">+</button>
        <button type="button" onClick={() => zoom(1 / 1.2)} aria-label="Zoom arrière">−</button>
        <button type="button" onClick={() => setView({ x: 0, y: 0, k: 1 })} aria-label="Recentrer">⟲</button>
      </div>
      <div className={styles.legend}>
        {["class", "method", "function"].map((k) => (
          <span key={k}><i style={{ background: colorOf(k) }} />{k}</span>
        ))}
      </div>
    </div>
  );
}
