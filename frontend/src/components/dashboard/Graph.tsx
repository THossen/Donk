import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Answer } from '../../api/types';
import { colorFor } from '../../utils/colors';
import { shortPath } from '../../utils/repo';
import Card from '../ui/Card';

export default function Graph({
  answer,
  liveFiles,
  onEvidence,
}: {
  answer: Answer | null;
  liveFiles: string[];
  onEvidence: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    if (!answer?.contributors?.length) return { nodes, edges };
    const contributors = answer.contributors.slice(0, 4);
    const byName = new Map(contributors.map((c) => [c.name, c]));
    // Aggregate each file's surviving lines across the shown contributors so
    // shared files rank by total weight, not by first-seen order.
    const owners = new Map<string, string[]>();
    const totals = new Map<string, number>();
    for (const c of contributors) {
      const counts = c.file_lines ?? {};
      for (const f of c.files.slice(0, 6)) {
        if (!owners.has(f)) owners.set(f, []);
        if (!owners.get(f)!.includes(c.name)) owners.get(f)!.push(c.name);
        totals.set(f, (totals.get(f) ?? 0) + (counts[f] ?? 0));
      }
    }
    const fileList = [...owners.keys()]
      .sort((a, b) => (totals.get(b) ?? 0) - (totals.get(a) ?? 0))
      .slice(0, 8);
    const rowH = 64;
    contributors.forEach((c, i) => {
      nodes.push({
        id: `c:${c.name}`,
        position: { x: 0, y: i * rowH },
        data: { label: c.name },
        style: {
          background: `${colorFor(c.name)}24`,
          color: '#000000',
          border: `2px solid ${colorFor(c.name)}`,
          borderRadius: 8,
          fontSize: 12,
          fontWeight: 600,
          width: 170,
        },
      });
    });
    fileList.forEach((f, j) => {
      const hot = liveFiles.includes(f);
      nodes.push({
        id: `f:${f}`,
        position: { x: 320, y: j * rowH - ((fileList.length - contributors.length) * rowH) / 2 },
        data: { label: shortPath(f) },
        style: {
          background: hot ? '#ccfbf1' : '#ffffff',
          color: '#000000',
          border: hot ? '2px solid #2dd4bf' : '1px solid #2a3442',
          borderRadius: 8,
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
          width: 250,
        },
      });
    });
    for (const f of fileList) {
      for (const name of owners.get(f)!) {
        const c = byName.get(name)!;
        const hot = liveFiles.includes(f);
        const share = (c.file_lines?.[f] ?? 0) / Math.max(1, c.surviving_lines);
        edges.push({
          id: `e:${name}:${f}`,
          source: `c:${name}`,
          target: `f:${f}`,
          animated: hot,
          style: { stroke: hot ? '#2dd4bf' : colorFor(name), strokeWidth: hot ? 2.5 : 1 + share * 2.5, opacity: hot ? 1 : 0.55 },
        });
      }
    }
    return { nodes, edges };
  }, [answer, liveFiles]);

  if (!answer?.contributors?.length) return null;
  return (
    <Card pad="sm">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 rounded-lg px-1 py-0.5 text-left"
      >
        <span className="text-sm font-medium text-slate-200">Contributor → code</span>
        <span className="ml-auto text-slate-400">{open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span>
      </button>
      {open && (
        <>
          <div className="mb-2 px-1 text-xs text-slate-500">
            From the current investigation only. Edge thickness is that contributor&apos;s surviving lines in the file; glowing edges track live tool results. Click a file node to inspect it.
          </div>
          <div className="h-80 w-full overflow-hidden rounded-lg border border-ink-700 bg-ink-950">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodeClick={(_, node) => {
                if (node.id.startsWith('f:')) {
                  const path = node.id.slice(2);
                  onEvidence(`s:${encodeURIComponent(path)}:1:40`);
                }
              }}
              fitView
              proOptions={{ hideAttribution: true }}
              colorMode="light"
            >
              <Background gap={24} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
        </>
      )}
    </Card>
  );
}
