import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { sendChatMessage } from '../lib/api';
import ChatBubble from '../components/ChatBubble';
import { MessageSquare, Send, Bot, Fuel, Wrench } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agente?: string;
  loading?: boolean;
}

const suggestedQuestions = [
  { text: '¿Qué buses tienen mayor consumo?', agente: 'combustible', icon: Fuel },
  { text: '¿Qué buses tienen riesgo mecánico?', agente: 'mantenimiento', icon: Wrench },
  { text: '¿Cuáles son las alertas prioritarias?', agente: 'mantenimiento', icon: Wrench },
  { text: '¿Cómo está la eficiencia de la flota?', agente: 'combustible', icon: Fuel },
];

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [agente, setAgente] = useState<'combustible' | 'mantenimiento'>('combustible');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-fill from bus selection on map
  useEffect(() => {
    const bus = searchParams.get('bus');
    if (bus && messages.length === 0) {
      setInput(`Analiza el estado del bus ${bus}`);
      inputRef.current?.focus();
    }
  }, [searchParams, messages.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string, agenteOverride?: string) => {
    const prompt = text || input.trim();
    if (!prompt || sending) return;

    const selectedAgente = agenteOverride || agente;
    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', content: prompt },
      { id: assistantMsgId, role: 'assistant', content: '', agente: selectedAgente, loading: true },
    ]);
    setInput('');
    setSending(true);

    try {
      const response = await sendChatMessage(prompt, selectedAgente);
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? { ...m, content: response.respuesta, loading: false, agente: response.agente_usado }
            : m
        )
      );
    } catch (err: any) {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? { ...m, content: `Error: ${err.message}`, loading: false }
            : m
        )
      );
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const lastAssistantId = [...messages].reverse().find(m => m.role === 'assistant')?.id;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-6 h-6 text-red-400" />
          <div>
            <h1 className="text-white font-bold">Chat con Agentes IA</h1>
            <p className="text-slate-400 text-xs">Consulta sobre combustible o mantenimiento</p>
          </div>
        </div>
        <div className="flex bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => setAgente('combustible')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
              agente === 'combustible' ? 'bg-amber-500/20 text-amber-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Fuel className="w-4 h-4" /> Combustible
          </button>
          <button
            onClick={() => setAgente('mantenimiento')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
              agente === 'mantenimiento' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Wrench className="w-4 h-4" /> Mantenimiento
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-16 h-16 text-slate-600 mb-4" />
            <h2 className="text-white text-xl font-bold mb-2">ADO MobilityIA</h2>
            <p className="text-slate-400 mb-6 max-w-md">
              Pregunta sobre el estado de la flota, consumo de combustible,
              riesgo mecánico o recomendaciones de mantenimiento.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-lg">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q.text, q.agente)}
                  className="flex items-center gap-2 p-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-left text-sm text-slate-300 transition-colors"
                >
                  <q.icon className="w-4 h-4 text-slate-500 shrink-0" />
                  {q.text}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <ChatBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            agente={msg.agente}
            loading={msg.loading}
            isLatest={msg.id === lastAssistantId}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/50 shrink-0">
        <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Pregunta sobre la flota..."
            disabled={sending}
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-slate-700 text-white rounded-xl transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
