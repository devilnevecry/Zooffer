import { redirect } from "next/navigation";

/** Password reset links are retired together with email/password accounts. */
export default function ResetPasswordPage() {
  redirect("/login");
}
