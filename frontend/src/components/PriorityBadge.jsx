import React from 'react';

export default function PriorityBadge({ level }) {
  let color = 'bg-slate-800 text-slate-300 border-slate-700';

  if (!level || level.includes('Routine')) {
    color = 'bg-emerald-950/60 text-emerald-300 border-emerald-800/40';
  } else if (level.includes('Low')) {
    color = 'bg-blue-950/60 text-blue-300 border-blue-800/40';
  } else if (level.includes('Medium')) {
    color = 'bg-yellow-950/60 text-yellow-300 border-yellow-800/40';
  } else if (level.includes('High')) {
    color = 'bg-orange-950/60 text-orange-300 border-orange-800/40';
  } else if (level.includes('Urgent')) {
    color = 'bg-red-950/80 text-red-300 border-red-700/60 font-bold';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${color}`}>
      {level || 'Routine Monitoring'}
    </span>
  );
}
