import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Answer } from '../../api/types';
import { colorFor } from '../../utils/colors';
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
    const files = new Map<string, { contributors: string[] }>();
    for (const c of contributors) {
      for (const f of c.files.slice(0, 6)) {
        const e = files.get(f) ?? { contributors: [] };
        e.contributors.push(c.name);
        files.set(f, e);
      }
    }
    const fileList = [...files.keys()].slice(0, 8);
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
        data: { label: f.length > 34 ? '…' + f.slice(-33) : f },
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
      for (const c of files.get(f)!.contributors) {
        const hot = liveFiles.includes(f);
        edges.push({
          id: `e:${c}:${f}`,
          source: `c:${c}`,
          target: `f:${f}`,
          animated: hot,
          style: { stroke: hot ? '#2dd4bf' : colorFor(c), strokeWidth: hot ? 2.5 : 1.5, opacity: hot ? 1 : 0.55 },
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
            From the current investigation only. Click a file node to inspect it. Highlighted edges track live tool results.
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
