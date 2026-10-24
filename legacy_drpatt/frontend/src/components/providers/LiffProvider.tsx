"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import liff from "@line/liff";

interface LiffContextType {
  liff: typeof liff | null;
  liffError: string | null;
  profile: any | null;
  isLoggedIn: boolean;
}

const LiffContext = createContext<LiffContextType>({
  liff: null,
  liffError: null,
  profile: null,
  isLoggedIn: false,
});

export const useLiff = () => useContext(LiffContext);

export const LiffProvider = ({ children }: { children: React.ReactNode }) => {
  const [liffObject, setLiffObject] = useState<typeof liff | null>(null);
  const [liffError, setLiffError] = useState<string | null>(null);
  const [profile, setProfile] = useState<any | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const initLiff = async () => {
      try {
        const liffId = process.env.NEXT_PUBLIC_LIFF_ID || process.env.NEXT_PUBLIC_LINE_LIFF_ID;
        if (!liffId) {
          console.warn("LIFF ID is missing in environment variables");
          setLiffError("LIFF is not configured");
          return;
        }

        await liff.init({ liffId });
        setLiffObject(liff);

        if (liff.isLoggedIn()) {
          setIsLoggedIn(true);
          const userProfile = await liff.getProfile();
          setProfile(userProfile);
        }
      } catch (err: any) {
        console.error("LIFF Initialization failed", err);
        setLiffError(err.message);
      }
    };

    initLiff();
  }, []);

  return (
    <LiffContext.Provider
      value={{
        liff: liffObject,
        liffError,
        profile,
        isLoggedIn,
      }}
    >
      {children}
    </LiffContext.Provider>
  );
};
