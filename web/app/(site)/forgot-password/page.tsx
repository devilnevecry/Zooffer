import { redirect } from "next/navigation";

/** Email recovery is not part of the product: sign-in is Telegram-only. */
export default function ForgotPasswordPage() {
  redirect("/login");
}
