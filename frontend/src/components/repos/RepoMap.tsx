import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Expand } from 'lucide-react';
import type { RepoMapData, RepoMapNode } from '../../api/types';
import { formatCompact } from '../../utils/format';

const W = 1000;
const ROW_H = 124;
const Y0 = 44;
const PILL_H = 30;
const ZOOM_MS = 900;
const yFor = (depth: number) => Y0 + depth * ROW_H;

const TINTS = ['#cfe6e3', '#d4e3f2', '#dce9d4', '#efe4c8', '#f0d9c6', '#e7d4dd', '#d9dfe8', '#e2d9c2'];

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface TNode {
  node: RepoMapNode;
  x: number;
  y: number;
  w: number;
  depth: number;
  tintIndex: number;
  expanded: boolean;
  hasKids: boolean;
  parent: TNode | null;
  children: TNode[];
}

/** Does directory `dir` contain file `file`? ("" matches only root files.) */
function contains(dir: string, file: string): boolean {
  if (dir === '') return !file.includes('/');
  return file === dir || file.startsWith(dir + '/');
}

function lighten(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16);
  const mix = (c: number) => Math.round(c + (255 - c) * amt);
  const r = mix((n >> 16) & 255);
  const g = mix((n >> 8) & 255);
  const b = mix(n & 255);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

/**
 * Tidy top-down layout. Each branch owns a horizontal slot sized by its
 * direct-child count, so expanding one branch never shifts the others.
 */
function buildLayout(data: RepoMapData, expanded: Set<RepoMapNode>, rootLabel: string): TNode[] {
  const weight = (k: RepoMapNode) => Math.max(1, k.children.length);
  const root: TNode = {
    node: data.tree,
    x: W / 2,
    y: yFor(0),
    w: Math.min(190, Math.max(110, rootLabel.length * 8 + 44)),
    depth: 0,
    tintIndex: -1,
    expanded: true,
    hasKids: data.tree.children.length > 0,
    parent: null,
    children: [],
  };
  const out: TNode[] = [root];
  const place = (kids: RepoMapNode[], x0: number, x1: number, depth: number, parent: TNode, tintBase: number) => {
    const total = kids.reduce((s, k) => s + weight(k), 0) || 1;
    let fx = x0;
    kids.forEach((k, i) => {
      const slot = ((x1 - x0) * weight(k)) / total;
      const cx = fx + slot / 2;
      fx += slot;
      const tintIndex = depth === 1 ? tintBase + i : tintBase;
      const t: TNode = {
        node: k,
        x: cx,
        y: yFor(depth),
        w: Math.min(depth === 1 ? 170 : 150, Math.max(depth === 1 ? 54 : 40, slot - (depth === 1 ? 12 : 8))),
        depth,
        tintIndex,
        expanded: expanded.has(k),
        hasKids: k.children.length > 0,
        parent,
        children: [],
      };
      parent.children.push(t);
      out.push(t);
      if (t.expanded && t.hasKids) {
        place(k.children, cx - slot / 2, cx + slot / 2, depth + 1, t, tintIndex);
      }
    });
  };
  place(data.tree.children, 0, W, 1, root, 0);
  return out;
}

const easeInOutCubic = (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export default function RepoMap({
  data,
  scope,
  hitPaths,
  rootLabel,
}: {
  data: RepoMapData;
  scope: string | null;
  hitPaths: string[];
  rootLabel?: string;
}) {
  const label = rootLabel || 'Whole repo';
  const [expanded, setExpanded] = useState<Set<RepoMapNode>>(new Set());
  const nodes = useMemo(() => buildLayout(data, expanded, label), [data, expanded, label]);
  const full = useMemo(() => {
    const maxDepth = nodes.reduce((m, n) => Math.max(m, n.depth), 0);
    return { x: 0, y: 0, w: W, h: Math.max(220, yFor(maxDepth) + PILL_H / 2 + 36) };
  }, [nodes]);
  const [open, setOpen] = useState(true);
  const [view, setView] = useState<Box>(() => {
    const laidOut = buildLayout(data, new Set(), label);
    const maxDepth = laidOut.reduce((m, n) => Math.max(m, n.depth), 0);
    return { x: 0, y: 0, w: W, h: Math.max(220, yFor(maxDepth) + PILL_H / 2 + 36) };
  });
  const [hover, setHover] = useState<TNode | null>(null);
  const viewRef = useRef<Box>(view);
  const animRef = useRef<number>(0);
  const reduced = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  );

  const stopAnim = () => {
    if (animRef.current) cancelAnimationFrame(animRef.current);
    animRef.current = 0;
  };
  useEffect(() => stopAnim, []);

  const clampView = (target: Box): Box => ({
    x: Math.max(0, Math.min(target.x, W - 40)),
    y: Math.max(0, Math.min(target.y, full.h - 40)),
    w: Math.max(200, Math.min(target.w, W)),
    h: Math.max(120, Math.min(target.h, full.h)),
  });

  const zoomTo = (target: Box, instant = false) => {
    const clamped = clampView(target);
    if (instant || reduced) {
      stopAnim();
      viewRef.current = clamped;
      setView(clamped);
      return;
    }
    stopAnim();
    const from = { ...viewRef.current };
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ZOOM_MS);
      const e = easeInOutCubic(t);
      const v = {
        x: from.x + (clamped.x - from.x) * e,
        y: from.y + (clamped.y - from.y) * e,
        w: from.w + (clamped.w - from.w) * e,
        h: from.h + (clamped.h - from.h) * e,
      };
      viewRef.current = v;
      setView(v);
      if (t < 1) animRef.current = requestAnimationFrame(step);
      else animRef.current = 0;
    };
    animRef.current = requestAnimationFrame(step);
  };

  // New repository: collapse everything and reset the camera.
  useEffect(() => {
    setExpanded(new Set());
    const laidOut = buildLayout(data, new Set(), label);
    const maxDepth = laidOut.reduce((m, n) => Math.max(m, n.depth), 0);
    const reset = { x: 0, y: 0, w: W, h: Math.max(220, yFor(maxDepth) + PILL_H / 2 + 36) };
    stopAnim();
    viewRef.current = reset;
    setView(reset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const pad = (b: Box): Box => {
    const px = Math.max(24, b.w * 0.08);
    const py = Math.max(16, b.h * 0.1);
    return { x: b.x - px, y: b.y - py, w: b.w + px * 2, h: b.h + py * 2 };
  };

  const pillBox = (t: TNode): Box => ({ x: t.x - t.w / 2, y: t.y - PILL_H / 2, w: t.w, h: PILL_H });

  const subtreeBox = (t: TNode): Box => {
    let box = pillBox(t);
    const grow = (n: TNode) => {
      for (const c of n.children) {
        const b = pillBox(c);
        const x = Math.min(box.x, b.x);
        const y = Math.min(box.y, b.y);
        box = { x, y, w: Math.max(box.x + box.w, b.x + b.w) - x, h: Math.max(box.y + box.h, b.y + b.h) - y };
        grow(c);
      }
    };
    grow(t);
    return box;
  };

  const matchIn = (list: TNode[], s: string): TNode | null => {
    let best: TNode | null = null;
    for (const t of list) {
      if (t.depth === 0) continue;
      const path = t.node.path;
      if (path === null) continue;
      const match = path === '' ? !s.includes('/') : s === path || s.startsWith(path + '/');
      if (!match) continue;
      const len = path.length;
      const bestLen = best?.node.path?.length ?? -1;
      if (!best || len > bestLen || (len === bestLen && t.depth < best.depth)) {
        best = t;
      }
    }
    return best;
  };

  // Expand to the answer's scope and glide there when a new answer lands.
  useEffect(() => {
    if (scope === null) return;
    if (scope === '') {
      zoomTo(full);
      return;
    }
    const next = new Set(expanded);
    const walk = (kids: RepoMapNode[]) => {
      for (const k of kids) {
        if (k.path === null) continue;
        const match = k.path === '' ? !scope.includes('/') : scope === k.path || scope.startsWith(k.path + '/');
        if (match && k.children.length > 0) {
          next.add(k);
          walk(k.children);
        }
      }
    };
    walk(data.tree.children);
    setExpanded(next);
    const laidOut = buildLayout(data, next, label);
    const target = matchIn(laidOut, scope);
    if (target) zoomTo(pad(subtreeBox(target)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

  const scopeNode = useMemo(() => {
    if (scope === null || scope === '') return null;
    return matchIn(nodes, scope);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, scope]);

  const scopeChain = useMemo(() => {
    const set = new Set<TNode>();
    let cur = scopeNode;
    while (cur) {
      set.add(cur);
      cur = cur.parent;
    }
    return set;
  }, [scopeNode]);

  const isHot = (t: TNode): boolean => {
    const path = t.node.path;
    if (t.depth === 0 || path === null || hitPaths.length === 0) return false;
    return hitPaths.some((f) => contains(path, f));
  };

  const toggle = (t: TNode) => {
    if (t.depth === 0) {
      zoomTo(full);
      return;
    }
    if (!t.hasKids) {
      zoomTo(pad(subtreeBox(t)));
      return;
    }
    const next = new Set(expanded);
    if (next.has(t.node)) next.delete(t.node);
    else next.add(t.node);
    setExpanded(next);
    const laidOut = buildLayout(data, next, label);
    const nt = laidOut.find((n) => n.node === t.node && n.depth === t.depth) ?? t;
    zoomTo(pad(subtreeBox(nt)));
  };

  const expandAll = () => {
    const all = new Set<RepoMapNode>();
    const walk = (kids: RepoMapNode[]) => {
      for (const k of kids) {
        if (k.children.length > 0) {
          all.add(k);
          walk(k.children);
        }
      }
    };
    walk(data.tree.children);
    setExpanded(all);
  };

  const zoomed = Math.abs(view.w - full.w) > 8 || Math.abs(view.h - full.h) > 8;
  const readout = hover ?? scopeNode;

  const fillFor = (t: TNode): string => {
    if (t === scopeNode) return '#ccfbf1';
    if (t.depth === 0) return '#ffffff';
    if (t.node.path === null) return t.depth === 1 ? '#dde3ea' : '#e8edf3';
    const base = TINTS[t.tintIndex % TINTS.length];
    return t.depth === 1 ? base : lighten(base, 0.45);
  };

  const labelFor = (t: TNode): string => {
    const name = t.depth === 0 ? label : t.node.name;
    const maxChars = Math.max(1, Math.floor((t.w - 22) / 7));
    return name.length > maxChars ? name.slice(0, Math.max(1, maxChars - 1)) + '…' : name;
  };

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mb-2 flex w-full items-center gap-2 rounded-lg px-1 py-0.5 text-left text-sm font-medium text-slate-200 hover:bg-ink-850"
      >
        {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        Repository tree
        <span className="font-mono text-xs font-normal text-slate-500">
          {data.mapped_files.toLocaleString()} files
        </span>
      </button>
      {open && (
      <>
      <svg
        viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
        className="h-72 w-full overflow-hidden rounded-lg border border-ink-700 bg-ink-900"
        role="img"
        aria-label="Repository tree"
        onClick={() => zoomTo(full)}
      >
        {nodes.length <= 1 && (
          <text x={W / 2} y={yFor(1)} textAnchor="middle" fontSize={15} fill="#000000">
            No tracked files mapped
          </text>
        )}
        {nodes
          .filter((t) => t.depth > 0)
          .map((t, i) => {
            const p = t.parent!;
            const x0 = p.x;
            const y0 = p.y + PILL_H / 2;
            const x1 = t.x;
            const y1 = t.y - PILL_H / 2;
            const onPath = scopeChain.has(t) && scopeChain.has(p);
            return (
              <path
                key={`e-${i}`}
                d={`M ${x0} ${y0} C ${x0} ${y0 + 42}, ${x1} ${y1 - 42}, ${x1} ${y1}`}
                fill="none"
                stroke={onPath ? '#0d9488' : '#c3cedd'}
                strokeWidth={onPath ? 2.5 : 1.5}
                vectorEffect="non-scaling-stroke"
              />
            );
          })}
        {nodes.map((t, i) => {
          const b = pillBox(t);
          const scoped = t === scopeNode;
          const hot = !scoped && isHot(t);
          return (
            <g
              key={i}
              role="button"
              tabIndex={0}
              aria-label={t.depth === 0 ? 'Reset repository tree view' : `Zoom to ${t.node.path || 'repo root'}`}
              onClick={(e) => {
                e.stopPropagation();
                toggle(t);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  e.stopPropagation();
                  toggle(t);
                }
              }}
              onMouseEnter={() => setHover(t.depth === 0 ? null : t)}
              onMouseLeave={() => setHover(null)}
              className="cursor-pointer"
            >
              <title>
                {t.depth === 0
                  ? `${label} · ${data.mapped_files.toLocaleString()} files`
                  : `${t.node.path || '(repo root)'} · ${t.node.files.toLocaleString()} files`}
              </title>
              <rect
                x={b.x}
                y={b.y}
                width={b.w}
                height={b.h}
                rx={15}
                fill={fillFor(t)}
                stroke={scoped || hot ? '#0d9488' : t.depth === 0 ? '#d8e0ea' : '#ffffff'}
                strokeWidth={scoped ? 3 : hot ? 2 : t.depth === 0 ? 1.5 : 2}
                vectorEffect="non-scaling-stroke"
              />
              <text x={t.x} y={t.y + 4.5} textAnchor="middle" fontSize={13} fontWeight={t.depth <= 1 ? 600 : 500} fill="#000000" pointerEvents="none">
                {labelFor(t)}
              </text>
              {t.hasKids && (
                <g pointerEvents="none">
                  <circle cx={b.x + b.w - 3} cy={b.y + b.h - 3} r={9} fill="#ffffff" stroke="#c3cedd" strokeWidth={1.5} />
                  <text x={b.x + b.w - 3} y={b.y + b.h + 1.5} textAnchor="middle" fontSize={12} fontWeight={700} fill="#000000">
                    {t.expanded ? '–' : '+'}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-1.5 flex items-center gap-2 font-mono text-xs text-slate-400">
        <span
          className="truncate"
          title={readout && readout.depth > 0 ? `${readout.node.path || '(repo root)'} · ${readout.node.files.toLocaleString()} files` : undefined}
        >
          {readout && readout.depth > 0
            ? `${readout.node.path || '(repo root)'} · ${formatCompact(readout.node.files)} files`
            : `Click a branch to expand · click a node to zoom${data.truncated ? ' · smaller dirs grouped' : ''}`}
        </span>
        <span className="ml-auto flex shrink-0 items-center gap-1">
          <button onClick={expandAll} className="rounded-full border border-ink-700 px-2 py-0.5 text-slate-300 hover:bg-ink-800">
            Expand all
          </button>
          <button onClick={() => setExpanded(new Set())} className="rounded-full border border-ink-700 px-2 py-0.5 text-slate-300 hover:bg-ink-800">
            Collapse
          </button>
          {zoomed && (
            <button
              onClick={() => zoomTo(full)}
              className="flex items-center gap-1 rounded-full border border-ink-700 px-2 py-0.5 text-slate-300 hover:bg-ink-800"
            >
              <Expand size={12} /> Whole repo
            </button>
          )}
        </span>
      </div>
      </>
      )}
    </div>
  );
}
