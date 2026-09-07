import { AuthenticatedShell } from "@/components/AuthenticatedShell";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return <AuthenticatedShell>{children}</AuthenticatedShell>;
}
