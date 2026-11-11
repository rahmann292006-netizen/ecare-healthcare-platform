"use client";

import { useEffect, useState } from "react";

export function useCurrentTime() {
  const [timestamp, setTimestamp] = useState(0);

  useEffect(() => {
    const updateTime = () => setTimestamp(Date.now());
    updateTime();
    const intervalId = window.setInterval(updateTime, 60_000);
    return () => window.clearInterval(intervalId);
  }, []);

  return timestamp;
}
