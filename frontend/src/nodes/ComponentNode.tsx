import React, { useState, useCallback } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export default function ComponentNode({ data, id }: NodeProps) {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState((data as any).label || "Component");

  const onBlur = useCallback(() => {
    setEditing(false);
    (data as any).label = label;
  }, [data, label]);

  return (
    <div
      style={{
        padding: "12px 20px",
        borderRadius: "8px",
        background: "#e0e7ff",
        border: "2px solid #6366f1",
        minWidth: "120px",
        textAlign: "center",
        fontSize: "0.9rem",
        fontWeight: 500,
      }}
    >
      <Handle type="target" position={Position.Top} />
      {editing ? (
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={onBlur}
          onKeyDown={(e) => e.key === "Enter" && onBlur()}
          autoFocus
          style={{ width: "100%", textAlign: "center", border: "none", background: "transparent", fontSize: "0.9rem" }}
        />
      ) : (
        <div onDoubleClick={() => setEditing(true)}>{label}</div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
