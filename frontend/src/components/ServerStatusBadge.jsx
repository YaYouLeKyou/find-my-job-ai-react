/**
 * ServerStatusBadge — pastille de statut du backend (Render cold start).
 *
 * - 'waking'  : orange pulsant "⏳ Réveil du serveur…" (ne bloque rien)
 * - 'online'  : vert "🟢 Serveur en ligne"
 * - 'offline' : rouge discret "🔴 Serveur injoignable — réessayez"
 */
export default function ServerStatusBadge({ status }) {
  if (status === 'online') {
    return (
      <span
        title="Backend Render en ligne"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.75rem',
          fontWeight: '700',
          color: '#2e7d32',
          background: 'rgba(76, 175, 80, 0.12)',
          border: '1px solid rgba(76, 175, 80, 0.3)',
          borderRadius: '9999px',
          padding: '4px 12px',
        }}
      >
        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#4caf50', display: 'inline-block' }} />
        Serveur en ligne
      </span>
    );
  }

  if (status === 'offline') {
    return (
      <span
        title="Backend injoignable après plusieurs tentatives"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.75rem',
          fontWeight: '700',
          color: '#c62828',
          background: 'rgba(244, 67, 54, 0.1)',
          border: '1px solid rgba(244, 67, 54, 0.3)',
          borderRadius: '9999px',
          padding: '4px 12px',
        }}
      >
        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#f44336', display: 'inline-block' }} />
        Serveur injoignable — réessayez dans un instant
      </span>
    );
  }

  // waking (défaut) : Render sort de veille, cold start ~30-60s
  return (
    <span
      title="Le serveur Render sort de veille (cold start, ~30-60s). Vous pouvez déjà naviguer."
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '0.75rem',
        fontWeight: '700',
        color: '#e65100',
        background: 'rgba(255, 152, 0, 0.12)',
        border: '1px solid rgba(255, 152, 0, 0.3)',
        borderRadius: '9999px',
        padding: '4px 12px',
      }}
    >
      <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#ff9800', display: 'inline-block', animation: 'pulse-dot 1.5s ease-in-out infinite' }} />
      Réveil du serveur…
    </span>
  );
}
