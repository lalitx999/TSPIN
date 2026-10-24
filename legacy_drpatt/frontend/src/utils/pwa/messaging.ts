import { getMessaging, getToken } from "firebase/messaging";
import { app } from "./client";

/**
 * Register firebase-messaging-sw.js and obtain the client's FCM Token
 * @param vapidKey Web Push Certificate Key (obtained from Firebase Console)
 */
export const getFCMToken = async (vapidKey: string): Promise<string | null> => {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    console.warn("Service workers are not supported in this environment.");
    return null;
  }

  try {
    // Register background service worker
    const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
    console.log("FCM Service Worker registered successfully:", registration);

    const messaging = getMessaging(app);
    const token = await getToken(messaging, {
      serviceWorkerRegistration: registration,
      vapidKey: vapidKey,
    });
    
    return token;
  } catch (error) {
    console.error("Failed to retrieve FCM Token:", error);
    return null;
  }
};
