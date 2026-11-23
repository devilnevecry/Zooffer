import { redirect } from "next/navigation";

/** Email verification is retired: Telegram is the only identity channel. */
export default function VerifyEmailPage() {
  redirect("/login");
}
