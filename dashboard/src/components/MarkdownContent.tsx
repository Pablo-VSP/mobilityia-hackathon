import Markdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ReactNode } from 'react';

// Custom components that wrap tables in a scrollable, bordered container
const mdComponents: Components = {
  table: ({ children }: { children?: ReactNode }) => (
    <div className="my-2 overflow-x-auto resize-x border border-slate-600 rounded-lg max-w-full">
      <table className="w-full border-collapse text-sm min-w-max">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }: { children?: ReactNode }) => (
    <thead className="bg-slate-700/60">{children}</thead>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-300 border-b border-slate-600 border-r border-r-slate-700/40 last:border-r-0 whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="px-3 py-1.5 text-slate-300 border-b border-slate-700/50 border-r border-r-slate-700/30 last:border-r-0 whitespace-nowrap">
      {children}
    </td>
  ),
  tr: ({ children }: { children?: ReactNode }) => (
    <tr className="hover:bg-slate-700/30 transition-colors">{children}</tr>
  ),
};

interface Props {
  children: string;
  className?: string;
  compact?: boolean;
}

export default function MarkdownContent({ children, className = '', compact = false }: Props) {
  const baseClasses = compact
    ? 'prose prose-sm prose-invert max-w-none prose-p:my-1 prose-p:text-slate-200 prose-headings:text-white prose-headings:text-sm prose-headings:mt-2 prose-headings:mb-1 prose-li:text-slate-200 prose-li:my-0 prose-ul:my-1 prose-strong:text-white prose-code:text-amber-300 prose-code:bg-slate-700 prose-code:px-1 prose-code:rounded'
    : 'prose prose-sm prose-invert max-w-none prose-p:text-slate-200 prose-p:leading-relaxed prose-p:my-1 prose-strong:text-white prose-li:text-slate-200 prose-li:my-0.5 prose-ul:my-1 prose-ol:my-1 prose-headings:text-white prose-headings:mt-3 prose-headings:mb-1 prose-code:text-amber-300 prose-code:bg-slate-700 prose-code:px-1 prose-code:rounded';

  return (
    <div className={`${baseClasses} ${className}`}>
      <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>
        {children}
      </Markdown>
    </div>
  );
}
