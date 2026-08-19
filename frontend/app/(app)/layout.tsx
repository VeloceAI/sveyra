import { AppNav } from "@/components/AppNav";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AppNav />
      <main>{children}</main>
    </>
  );
}
