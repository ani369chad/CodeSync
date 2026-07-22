interface Participant {
  clientId: string;
  name: string;
  color: string;
}

interface Props {
  self: { name: string; color: string };
  participants: Participant[];
  maxCollaborators: number;
}

export default function PresenceBar({ self, participants, maxCollaborators }: Props) {
  const others = participants;
  const total = others.length + 1;

  return (
    <div className="presence-bar">
      <div className="presence-avatars">
        <span className="presence-dot self" style={{ background: self.color }} title={`${self.name} (you)`}>
          {self.name.slice(0, 1).toUpperCase()}
        </span>
        {others.map((p) => (
          <span key={p.clientId} className="presence-dot" style={{ background: p.color }} title={p.name}>
            {p.name.slice(0, 1).toUpperCase()}
          </span>
        ))}
      </div>
      <span className="presence-count">
        {total} / {maxCollaborators} collaborators
      </span>
    </div>
  );
}
