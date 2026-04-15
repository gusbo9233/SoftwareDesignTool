import React, { useState, useCallback } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export default function ErEntityNode({ data }: NodeProps) {
  const d = data as any;
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(d.label || "Entity");
  const [attributes, setAttributes] = useState<string[]>(d.attributes || []);

  const save = useCallback(() => {
    setEditing(false);
    d.label = label;
    d.attributes = attributes;
  }, [d, label, attributes]);

  return (
    <div
      style={{
        borderRadius: "4px",
        background: "#fff",
        border: "2px solid #059669",
        minWidth: "150px",
        fontSize: "0.85rem",
      }}
    >
      <Handle type="target" position={Position.Top} id="top-target" />
      <Handle type="source" position={Position.Top} id="top-source" />
      <Handle type="target" position={Position.Right} id="right-target" />
      <Handle type="source" position={Position.Right} id="right-source" />
      <Handle type="target" position={Position.Left} id="left-target" />
      <Handle type="source" position={Position.Left} id="left-source" />
      <div
        style={{
          padding: "8px 10px",
          fontWeight: 600,
          textAlign: "center",
          background: "#d1fae5",
          borderBottom: "1px solid #059669",
        }}
        onDoubleClick={() => setEditing(true)}
      >
        {editing ? (
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={save}
            onKeyDown={(e) => e.key === "Enter" && save()}
            autoFocus
            style={{ width: "100%", textAlign: "center", border: "none", background: "transparent", fontWeight: 600 }}
          />
        ) : (
          label
        )}
      </div>
      <div style={{ padding: "6px 10px", textAlign: "left" }}>
        {attributes.map((attr, i) => (
          <div key={i} style={{ fontSize: "0.8rem" }}>
            {attr}
          </div>
        ))}
        {attributes.length === 0 && <div style={{ color: "#999", fontSize: "0.8rem" }}>No attributes</div>}
      </div>
      <Handle type="target" position={Position.Bottom} id="bottom-target" />
      <Handle type="source" position={Position.Bottom} id="bottom-source" />
    </div>
  );
}
