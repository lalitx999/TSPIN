import { NextResponse } from "next/server";
import * as admin from "firebase-admin";
import { getDbAdmin } from "@/utils/firebase/admin";

/**
 * Server-side API endpoint to dispatch Firebase Cloud Messaging (FCM) notifications.
 * Bypasses client-side credential exposure by using Firebase Admin SDK.
 */
export async function POST(req: Request) {
  try {
    const { token, title, body } = await req.json();

    if (!token || !title || !body) {
      return NextResponse.json({ error: "Missing required fields: token, title, body" }, { status: 400 });
    }

    // Initialize Firebase Admin if not already active
    getDbAdmin();

    const message = {
      notification: {
        title: title,
        body: body,
      },
      token: token,
    };

    // Dispatch message via Admin SDK
    const response = await admin.messaging().send(message);
    console.log("✅ FCM Push Notification sent successfully:", response);

    return NextResponse.json({ success: true, messageId: response });
  } catch (error: any) {
    console.error("❌ FCM Push Notification Dispatch Failed:", error);
    return NextResponse.json({ error: "Failed to dispatch notification: " + error.message }, { status: 500 });
  }
}
