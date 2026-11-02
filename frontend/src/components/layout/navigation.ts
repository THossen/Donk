import { FolderGit2, Inbox, LayoutDashboard, type LucideIcon } from 'lucide-react';

export type Page = 'dashboard' | 'activity' | 'repos';

export interface PageMeta {
  id: Page;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
}

export const PAGES: PageMeta[] = [
  { id: 'dashboard', label: 'Dashboard', shortLabel: 'Dashboard', icon: LayoutDashboard },
  { id: 'activity', label: 'Activity', shortLabel: 'Activity', icon: Inbox },
  { id: 'repos', label: 'Repositories', shortLabel: 'Repos', icon: FolderGit2 },
];
