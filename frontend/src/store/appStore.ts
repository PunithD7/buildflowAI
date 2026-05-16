import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../services/api';

export interface Project {
  id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  created_at: number;
  workflow_count: number;
}

export interface Workflow {
  workflow_id: string;
  project_id: string;
  user_input: string;
  status: string;
  created_at: number;
  outputs?: Record<string, any>;
  agents_completed?: number;
  agents_failed?: number;
  total_agents?: number;
  stages_completed?: number;
}

export interface LogEntry {
  id: string;
  level: string;
  message: string;
  source?: string;
  workflow_id?: string;
  timestamp: number;
}

export interface AgentEvent {
  agent: string;
  event: string;
  payload: Record<string, any>;
  workflow_id: string;
  timestamp: number;
}

interface AppState {
  // Auth
  isAuthenticated: boolean;
  user: { id: string; email: string; name: string; role: string } | null;
  token: string | null;

  // Projects
  projects: Project[];
  selectedProject: Project | null;

  // Workflows
  workflows: Workflow[];
  activeWorkflow: Workflow | null;

  // Logs
  logs: LogEntry[];
  agentEvents: AgentEvent[];

  // UI State
  sidebarCollapsed: boolean;
  activeTab: string;
  isLoading: boolean;
  error: string | null;

  // Security Events
  securityEvents: any[];
  ddosStats: any;
  rateLimitEvents: any[];

  // Actions
  autoLogin: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadProjects: () => Promise<void>;
  createProject: (data: { name: string; description: string; type: string }) => Promise<Project>;
  loadWorkflows: () => Promise<void>;
  startWorkflow: (projectId: string, userInput: string) => Promise<Workflow>;
  addLog: (entry: Omit<LogEntry, 'id'>) => void;
  addAgentEvent: (event: AgentEvent) => void;
  addSecurityEvent: (event: any) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveTab: (tab: string) => void;
  setActiveWorkflow: (workflow: Workflow | null) => void;
  clearLogs: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      user: null,
      token: null,
      projects: [],
      selectedProject: null,
      workflows: [],
      activeWorkflow: null,
      logs: [],
      agentEvents: [],
      sidebarCollapsed: false,
      activeTab: 'dashboard',
      isLoading: false,
      error: null,
      securityEvents: [],
      ddosStats: null,
      rateLimitEvents: [],

      autoLogin: async () => {
        const { token } = get();
        if (token) {
          try {
            const user = await api.get('/auth/me', token);
            set({ isAuthenticated: true, user });
          } catch {
            set({ isAuthenticated: false, user: null, token: null });
          }
        } else {
          // Auto-demo login for showcase
          try {
            const response = await api.post('/auth/demo-login', {});
            set({
              isAuthenticated: true,
              user: response.user,
              token: response.access_token,
            });
          } catch (e) {
            console.warn('Demo login failed:', e);
          }
        }
      },

      login: async (email: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        const response = await api.postForm('/auth/login', formData);
        set({
          isAuthenticated: true,
          user: response.user,
          token: response.access_token,
        });
      },

      logout: () => {
        set({
          isAuthenticated: false,
          user: null,
          token: null,
          projects: [],
          workflows: [],
          activeWorkflow: null,
          logs: [],
        });
      },

      loadProjects: async () => {
        set({ isLoading: true });
        try {
          const projects = await api.get('/projects', get().token);
          set({ projects, isLoading: false });
        } catch (e) {
          set({ isLoading: false, error: String(e) });
        }
      },

      createProject: async (data) => {
        const project = await api.post('/projects', data, get().token);
        set((state) => ({ projects: [project, ...state.projects] }));
        return project;
      },

      loadWorkflows: async () => {
        try {
          const workflows = await api.get('/workflows', get().token);
          set({ workflows });
        } catch (e) {
          console.error('Failed to load workflows:', e);
        }
      },

      startWorkflow: async (projectId: string, userInput: string) => {
        const workflow = await api.post('/workflows', {
          project_id: projectId,
          user_input: userInput,
          user_id: get().user?.id || 'anonymous',
        }, get().token);
        
        set((state) => ({
          workflows: [workflow, ...state.workflows],
          activeWorkflow: workflow,
        }));
        return workflow;
      },

      addLog: (entry) => {
        const log: LogEntry = { ...entry, id: crypto.randomUUID() };
        set((state) => ({
          logs: [log, ...state.logs].slice(0, 500), // Keep last 500 logs
        }));
      },

      addAgentEvent: (event) => {
        set((state) => ({
          agentEvents: [event, ...state.agentEvents].slice(0, 200),
        }));
      },

      addSecurityEvent: (event) => {
        set((state) => ({
          securityEvents: [event, ...state.securityEvents].slice(0, 100),
        }));
      },

      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setActiveTab: (tab) => set({ activeTab: tab }),
      setActiveWorkflow: (workflow) => set({ activeWorkflow: workflow }),
      clearLogs: () => set({ logs: [], agentEvents: [] }),
    }),
    {
      name: 'buildflow-store',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
