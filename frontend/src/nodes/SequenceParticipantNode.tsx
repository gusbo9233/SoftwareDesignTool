import React, { useEffect, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

type SequenceParticipantKind = "actor" | "participant" | "boundary" | "control" | "entity";

const stylesByKind: Record<SequenceParticipantKind, React.CSSProperties> = {
  actor: {
    background: "#fef3c7",
    border: "2px solid #b45309",
    borderRadius: "999px",
  },
  participant: {
    background: "#e0e7ff",
    border: "2px solid #4f46e5",
    borderRadius: "10px",
  },
  boundary: {
    background: "#dcfce7",
    border: "2px solid #15803d",
    borderRadius: "10px",
  },
  control: {
    background: "#fce7f3",
    border: "2px solid #be185d",
    borderRadius: "10px",
  },
  entity: {
    background: "#e0f2fe",
    border: "2px solid #0369a1",
    borderRadius: "10px",
  },
};

export default function SequenceParticipantNode({ data }: NodeProps) {
  const d = data as {
    label?: string;
    kind?: SequenceParticipantKind;
    onChange?: (patch: { label: string }) => void;
  };
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(d.label || "Participant");

  useEffect(() => {
    if (!editing) {
      setLabel(d.label || "Participant");
    }
  }, [d.label, editing]);

  const save = () => {
    setEditing(false);
    d.onChange?.({ label: label.trim() || "Participant" });
  };

  const kind = d.kind || "participant";

  return (
    <div
      style={{
        position: "relative",
        minWidth: "150px",
        paddingBottom: "210px",
      }}
    >
      <Handle type="target" position={Position.Left} id="left-target" />
      <Handle type="source" position={Position.Right} id="right-source" />
      <Handle type="target" position={Position.Top} id="top-target" />
      <Handle type="source" position={Position.Bottom} id="bottom-source" />

      <div
        style={{
          ...stylesByKind[kind],
          minHeight: "54px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "10px 14px",
          textAlign: "center",
          fontSize: "0.9rem",
          fontWeight: 600,
          boxShadow: "0 6px 14px rgba(15, 23, 42, 0.08)",
        }}
        onDoubleClick={() => setEditing(true)}
      >
        {editing ? (
          <input
            className="nodrag nopan"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            onBlur={save}
            onKeyDown={(event) => {
              if (event.key === "Enter") save();
              if (event.key === "Escape") setEditing(false);
            }}
            autoFocus
            style={{
              width: "100%",
              textAlign: "center",
              border: "none",
              background: "transparent",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          />
        ) : (
          label
        )}
      </div>

      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "58px",
          bottom: "8px",
          width: "2px",
          transform: "translateX(-50%)",
          backgroundImage: "linear-gradient(to bottom, rgba(100,116,139,0.9) 50%, rgba(255,255,255,0) 0%)",
          backgroundPosition: "left",
          backgroundSize: "2px 12px",
          backgroundRepeat: "repeat-y",
        }}
      />
    </div>
  );
}
