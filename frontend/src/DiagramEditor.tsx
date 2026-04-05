import React, { useCallback, useEffect, useState, useRef } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type NodeTypes,
  BackgroundVariant,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import ComponentNode from "./nodes/ComponentNode";
import UmlClassNode from "./nodes/UmlClassNode";
import ErEntityNode from "./nodes/ErEntityNode";
import WorkflowStateNode from "./nodes/WorkflowStateNode";

const nodeTypes: NodeTypes = {
  component: ComponentNode,
  umlClass: UmlClassNode,
  erEntity: ErEntityNode,
  workflowState: WorkflowStateNode,
};

interface Props {
  diagramId: string;
  projectId: string;
  diagramType: string;
}

const NODE_TEMPLATES: Record<string, () => Partial<Node>> = {
  architecture: () => ({
    type: "component",
    data: { label: "Component" },
  }),
  uml_class: () => ({
    type: "umlClass",
    data: { label: "ClassName", attributes: ["- field: type"], methods: ["+ method(): void"] },
  }),
  er: () => ({
    type: "erEntity",
    data: { label: "Entity", attributes: ["id: PK", "name: string"] },
  }),
  workflow: () => ({
    type: "workflowState",
    data: { label: "State" },
  }),
};

export default function DiagramEditor({ diagramId, projectId, diagramType }: Props) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const nextId = useRef(1);

  useEffect(() => {
    if (!diagramId) return;
    fetch(`/api/diagrams/${diagramId}`)
      .then((r) => r.json())
      .then((data) => {
        setNodes(data.data?.nodes || []);
        setEdges(data.data?.edges || []);
        const maxId = (data.data?.nodes || []).reduce(
          (max: number, n: Node) => Math.max(max, parseInt(n.id, 10) || 0),
          0
        );
        nextId.current = maxId + 1;
      });
  }, [diagramId]);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect: OnConnect = useCallback(
    (connection) =>
      setEdges((eds) =>
        addEdge({ ...connection, id: `e${connection.source}-${connection.target}` }, eds)
      ),
    []
  );

  const addNode = useCallback(() => {
    const template = NODE_TEMPLATES[diagramType] || NODE_TEMPLATES.architecture;
    const newNode: Node = {
      id: String(nextId.current++),
      position: { x: 100 + Math.random() * 300, y: 100 + Math.random() * 300 },
      ...template(),
    } as Node;
    setNodes((nds) => [...nds, newNode]);
  }, [diagramType]);

  const save = useCallback(async () => {
    if (!diagramId) return;
    setSaving(true);
    setStatus("");
    try {
      const resp = await fetch(`/api/diagrams/${diagramId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: { nodes, edges } }),
      });
      if (resp.ok) {
        setStatus("Saved");
      } else {
        setStatus("Save failed");
      }
    } catch {
      setStatus("Save failed");
    }
    setSaving(false);
    setTimeout(() => setStatus(""), 2000);
  }, [diagramId, nodes, edges]);

  return (
    <div style={{ width: "100%", height: "600px", border: "1px solid #e5e5e5", borderRadius: "8px" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode={["Backspace", "Delete"]}
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Panel position="top-right">
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button onClick={addNode} className="btn btn-primary" style={{ fontSize: "0.85rem" }}>
              + Add Node
            </button>
            <button onClick={save} disabled={saving} className="btn" style={{ fontSize: "0.85rem" }}>
              {saving ? "Saving..." : "Save"}
            </button>
            {status && <span style={{ fontSize: "0.8rem", color: "#059669" }}>{status}</span>}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
