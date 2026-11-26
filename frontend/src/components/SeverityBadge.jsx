import React from 'react';

export default function SeverityBadge({ level, score }) {
  let color = 'bg-slate-800 text-slate-300 border-slate-700';

  if (!level || level.includes('No Visible')) {
    color = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
  } else if (level.includes('Minor')) {
    color = 'bg-blue-500/15 text-blue-400 border-blue-500/30';
  } else if (level.includes('Moderate')) {
    color = 'bg-amber-500/15 text-amber-400 border-amber-500/30';
  } else if (level.includes('Severe')) {
    color = 'bg-orange-500/15 text-orange-400 border-orange-500/30';
  } else if (level.includes('Critical')) {
    color = 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {level || 'Unknown'}
      {score !== undefined && score !== null && (
        <span className="opacity-80 font-mono text-[11px]">({score})</span>
      )}
    </span>
  );
}
