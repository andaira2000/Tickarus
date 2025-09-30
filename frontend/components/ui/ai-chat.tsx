'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Send, Bot, User, Loader2, MessageSquare, X, Minimize2 } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormControl, FormField, FormItem, FormMessage } from '@/components/ui/form';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';
import { ChatSession, ChatMessage, ChatMessageCreate } from '@/lib/types';

const messageSchema = z.object({
  content: z.string().min(1, 'Message cannot be empty').max(4000, 'Message too long'),
});

type MessageFormData = z.infer<typeof messageSchema>;

interface AIChatProps {
  ticketId: string;
  className?: string;
}

export function AIChat({ ticketId, className }: AIChatProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const form = useForm<MessageFormData>({
    resolver: zodResolver(messageSchema),
    defaultValues: {
      content: '',
    },
  });

  const { data: sessions } = useQuery({
    queryKey: ['chat-sessions', ticketId],
    queryFn: () => apiClient.getTicketChatSessions(ticketId),
    enabled: isOpen,
  });

  const { data: sessionData, isLoading: messagesLoading } = useQuery({
    queryKey: ['chat-session', currentSession?.id],
    queryFn: () => currentSession ? apiClient.getChatSession(currentSession.id) : null,
    enabled: !!currentSession,
  });

  const messages = sessionData?.messages || [];

  const createSessionMutation = useMutation({
    mutationFn: (initialMessage?: string) =>
      apiClient.createChatSession({
        ticket_id: ticketId,
        initial_message: initialMessage,
      }),
    onSuccess: (session) => {
      setCurrentSession(session);
      queryClient.invalidateQueries({ queryKey: ['chat-sessions', ticketId] });
      if (!form.getValues().content) {
        form.reset();
      }
    },
    onError: () => {
      toast.error('Failed to start AI chat');
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: ({ sessionId, messageData }: { sessionId: string; messageData: ChatMessageCreate }) =>
      apiClient.sendChatMessage(sessionId, messageData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-session', currentSession?.id] });
      form.reset();
    },
    onError: () => {
      toast.error('Failed to send message');
    },
  });

  const onSubmit = (data: MessageFormData) => {
    if (!currentSession) {
      createSessionMutation.mutate(data.content);
    } else {
      sendMessageMutation.mutate({
        sessionId: currentSession.id,
        messageData: { content: data.content, role: 'user' },
      });
    }
  };

  const startNewChat = () => {
    setCurrentSession(null);
    form.reset();
  };

  const selectSession = (session: ChatSession) => {
    setCurrentSession(session);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!currentSession && sessions && sessions.length > 0) {
      setCurrentSession(sessions[0]);
    }
  }, [sessions, currentSession]);

  const isPending = createSessionMutation.isPending || sendMessageMutation.isPending;

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 shadow-lg flex items-center justify-center transition-all hover:scale-110 z-50"
        aria-label="AI Assistant"
      >
        <Bot className="w-6 h-6 text-white" />
      </button>

      {isOpen && (
        <div className="fixed bottom-24 right-6 w-96 h-[32rem] bg-white rounded-lg shadow-2xl z-50 flex flex-col">
          <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-purple-500 to-blue-500 rounded-t-lg">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center">
                <Bot className="w-4 h-4 text-purple-600" />
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm">AI Assistant</h3>
                {currentSession && (
                  <Badge variant="secondary" className="text-xs bg-white/20 text-white border-0">
                    Active
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-1">
              {sessions && sessions.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={startNewChat}
                  title="Start new chat"
                  className="text-white hover:bg-white/20"
                >
                  <MessageSquare className="w-4 h-4" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsOpen(false)}
                className="text-white hover:bg-white/20"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {sessions && sessions.length > 1 && (
              <div className="flex flex-wrap gap-2 pb-2 border-b">
                {sessions.slice(0, 3).map((session) => (
                  <Button
                    key={session.id}
                    variant={currentSession?.id === session.id ? "default" : "outline"}
                    size="sm"
                    onClick={() => selectSession(session)}
                    className="text-xs"
                  >
                    {session.title || `Chat ${new Date(session.created_at).toLocaleDateString()}`}
                  </Button>
                ))}
              </div>
            )}

            {messagesLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
              </div>
            ) : messages.length > 0 ? (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-3 py-2 ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : message.role === 'assistant'
                        ? 'bg-gray-100 text-gray-900'
                        : 'bg-yellow-50 text-yellow-800 text-sm'
                    }`}
                  >
                    <div className="flex items-start space-x-2">
                      {message.role === 'assistant' && (
                        <div className="w-6 h-6 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Bot className="w-3 h-3 text-white" />
                        </div>
                      )}
                      {message.role === 'user' && (
                        <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <User className="w-3 h-3 text-gray-600" />
                        </div>
                      )}
                      <div className="whitespace-pre-wrap text-sm">
                        {message.content}
                      </div>
                    </div>
                    <div className={`text-xs mt-1 ${
                      message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {new Date(message.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 text-sm">
                No messages yet. Start a conversation with the AI!
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 border-t bg-gray-50 rounded-b-lg">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-2">
                <FormField
                  control={form.control}
                  name="content"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Textarea
                          placeholder="Ask the AI about this ticket..."
                          className="min-h-[60px] text-sm resize-none"
                          disabled={isPending}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex justify-between items-center">
                  <div className="text-xs text-gray-500">
                    {currentSession ? 'Continue conversation' : 'Start new chat'}
                  </div>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={isPending}
                    className="flex items-center space-x-1 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
                  >
                    {isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    <span>{isPending ? 'Sending...' : 'Send'}</span>
                  </Button>
                </div>
              </form>
            </Form>
          </div>
        </div>
      )}
    </>
  );
}