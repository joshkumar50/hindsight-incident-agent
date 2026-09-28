import { useEffect, useState } from 'react';

export const LiveIndicator = ({ updatedAt }: { updatedAt?: number }) => {
  const [secondsAgo, setSecondsAgo] = useState(0);

  useEffect(() => {
    if (!updatedAt) return;
    const interval = setInterval(() => {
      setSecondsAgo(Math.floor((Date.now() - updatedAt) / 1000));
    }, 1000);
    setSecondsAgo(Math.floor((Date.now() - updatedAt) / 1000));
    return () => clearInterval(interval);
  }, [updatedAt]);

  if (!updatedAt) {
    return <div className="text-xs text-slate-500">Connecting...</div>;
  }

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      <span>Live · updated {secondsAgo}s ago</span>
    </div>
  );
};
