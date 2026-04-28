import { useTypingEffect } from '../hooks/useTypingEffect';
import MarkdownContent from './MarkdownContent';
import { Bot, User, Fuel, Wrench, Loader2 } from 'lucide-react';

interface Props {
  role: 'user' | 'assistant';
  content: string;
  agente?: string;
  loading?: boolean;
  isLatest?: boolean;
}

export default function ChatBubble({ role, content, agente, loading, isLatest }: Props) {
  // Only animate the latest assistant message
  const shouldAnimate = role === 'assistant' && isLatest && !loading && content.length > 0;
  const { displayed, done } = useTypingEffect(shouldAnimate ? content : '', 15);
  const text = shouldAnimate ? displayed : content;

  if (role === 'user') {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[70%] rounded-2xl px-4 py-3 bg-red-600 text-white">
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        </div>
        <div className="w-8 h-8 bg-slate-700 rounded-lg flex items-center justify-center shrink-0 mt-1">
          <User className="w-4 h-4 text-slate-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 justify-start">
      <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center shrink-0 mt-1">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="max-w-[75%] rounded-2xl px-4 py-3 bg-slate-800 border border-slate-700">
        {loading ? (
          <div className="flex items-center gap-2 text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Analizando con agente de {agente}...</span>
          </div>
        ) : (
          <>
            <MarkdownContent>{text}</MarkdownContent>
            {shouldAnimate && !done && (
              <span className="inline-block w-2 h-4 bg-red-500 animate-pulse ml-0.5 align-middle" />
            )}
            {agente && done && (
              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1 border-t border-slate-700 pt-2">
                {agente.includes('combustible') && <><Fuel className="w-3 h-3 text-amber-400" /><span className="text-amber-400">Combustible</span></>}
                {agente.includes(',') && <span className="mx-1">+</span>}
                {agente.includes('mantenimiento') && <><Wrench className="w-3 h-3 text-blue-400" /><span className="text-blue-400">Mantenimiento</span></>}
                {!agente.includes('combustible') && !agente.includes('mantenimiento') && <span>Agente: {agente}</span>}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
