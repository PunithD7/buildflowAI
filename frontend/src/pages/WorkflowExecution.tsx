import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CheckCircle, XCircle, Circle, Clock, Zap, Terminal,
  ChevronDown, ChevronRight, Download, ArrowLeft, RefreshCw,
  AlertTriangle, ShieldAlert, RotateCcw, Activity,
  FolderOpen, FileCode, FileText, Package
} from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { createWorkflowWebSocket, api } from '../services/api';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';

const AGENT_SEQUENCE = [
  // Stage 1-7: Planning & Design (original 13)
  'Goal Understanding Agent', 'Planning Agent', 'Research Agent',
  'Strategy Agent', 'Architecture Agent', 'Tech Stack Agent',
  'Frontend Agent', 'Backend Agent', 'Security Agent',
  'Documentation Agent', 'Monitoring Agent', 'Self-Healing Agent', 'Rollback Agent',
  // Stage 8: Code Generation (new 3)
  'Frontend Code Agent', 'Backend Code Agent', 'Scaffolding Agent',
];

type AgentStatus = 'idle' | 'running' | 'completed' | 'failed' | 'skipped';

interface AgentState {
  name: string;
  status: AgentStatus;
  startTime?: number;
  endTime?: number;
  error?: string;
}

export function WorkflowExecution() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const { logs, addLog, addAgentEvent, token } = useAppStore();
  const navigate = useNavigate();

  const [workflow, setWorkflow] = useState<any>(null);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>(
    Object.fromEntries(AGENT_SEQUENCE.map(name => [name, { name, status: 'idle' }]))
  );
  const [outputs, setOutputs] = useState<Record<string, any>>({});
  const [activeOutput, setActiveOutput] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [workflowLogs, setWorkflowLogs] = useState<any[]>([]);
  // Files tab state
  const [activeTab, setActiveTab] = useState<'outputs' | 'files'>('outputs');
  const [filesReady, setFilesReady] = useState(false);
  const [fileTree, setFileTree] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileContentLoading, setFileContentLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);

  useEffect(() => {
    if (!workflowId) return;
    fetchWorkflow();
    const ws = connectWebSocket();
    return () => ws?.close();
  }, [workflowId]);

  const fetchWorkflow = async () => {
    try {
      const data = await api.get(`/workflows/${workflowId}`, token);
      setWorkflow(data);
      if (data.outputs) {
        setOutputs(data.outputs);
      }
    } catch (e) {
      console.error('Failed to fetch workflow:', e);
    }
  };

  const connectWebSocket = () => {
    if (!workflowId) return;

    try {
      const ws = createWorkflowWebSocket(workflowId, (data) => {
        setWsConnected(true);
        handleWsMessage(data);
      });
      return ws;
    } catch (e) {
      console.error('WebSocket failed:', e);
    }
  };

  const handleWsMessage = (data: any) => {
    // DEBUG: Log every message for troubleshooting
    console.log('[WebSocket Event]', data.type, data);

    const timestamp = data.timestamp || Date.now() / 1000;
    const logEntry = { timestamp, level: data.level || 'info', message: data.message || '', source: data.agent };

    // Handle replay markers
    if (data.type === 'replay_start') {
      console.log(`[WebSocket] 🔄 Replaying ${data.event_count} events...`);
      return;
    }
    if (data.type === 'replay_end') {
      console.log('[WebSocket] ✅ Replay complete.');
      return;
    }

    if (data.type === 'log') {
      setWorkflowLogs(prev => [{ ...logEntry, id: crypto.randomUUID() }, ...prev].slice(0, 300));
      addLog({ ...logEntry, workflow_id: workflowId });
    }

    if (data.type === 'agent_event') {
      const { agent, event, payload } = data;
      addAgentEvent(data);

      setAgentStates(prev => {
        const updated = { ...prev };
        if (event === 'started') {
          updated[agent] = { name: agent, status: 'running', startTime: timestamp };
        } else if (event === 'completed') {
          updated[agent] = { ...updated[agent], status: 'completed', endTime: timestamp };
        } else if (event === 'failed') {
          updated[agent] = { ...updated[agent], status: 'failed', endTime: timestamp, error: payload?.error };
        } else if (event === 'retrying') {
          updated[agent] = { ...updated[agent], status: 'running' };
        }
        return updated;
      });

      // Handle live output updates when an agent completes
      if (event === 'completed' && payload?.data) {
        const mapping: Record<string, string> = {
          "Goal Understanding Agent": "goal_analysis",
          "Planning Agent": "project_plan",
          "Research Agent": "market_research",
          "Strategy Agent": "strategy",
          "Architecture Agent": "system_architecture",
          "Tech Stack Agent": "tech_stack",
          "Frontend Agent": "frontend_design",
          "Backend Agent": "backend_design",
          "Security Agent": "security_design",
          "Documentation Agent": "documentation",
          "Monitoring Agent": "monitoring_strategy",
          "Self-Healing Agent": "resilience_design",
          "Rollback Agent": "deployment_strategy",
        };
        const outputKey = mapping[agent] || agent.replace(/ Agent$/, '').toLowerCase().replace(/ /g, '_');
        
        console.log(`[WebSocket] 📦 Updating live output for: ${outputKey}`);
        setOutputs(prev => ({ ...prev, [outputKey]: payload.data }));
        
        // Auto-select if nothing is selected yet
        setActiveOutput(current => current || outputKey);
      }
    }

    if (data.type === 'stage_started') {
      console.log(`[WebSocket] 🏁 Stage ${data.stage} started`);
      setCurrentStage(data.stage);
    }

    if (data.type === 'workflow_completed') {
      console.log('[WebSocket] 🎉 Workflow completed!', data.status);
      if (data.outputs) {
        setOutputs(data.outputs);
      }
      setWorkflow((prev: any) => ({ ...prev, status: data.status }));
    }

    // NEW: Handle files_ready event from orchestrator post-stage file writing
    if (data.type === 'files_ready') {
      console.log('[WebSocket] 📁 Files ready!', data.file_count, 'files generated');
      setFilesReady(true);
      // Auto-switch to Files tab when files are ready
      setActiveTab('files');
      // Load file tree
      loadFileTree();
    }
  };

  // Build React Flow graph — 8 stages including code generation
  const buildFlowGraph = (): { nodes: any[]; edges: any[] } => {
    const stages = [
      ['Goal Understanding Agent'],
      ['Planning Agent', 'Research Agent'],
      ['Strategy Agent'],
      ['Architecture Agent', 'Tech Stack Agent'],
      ['Frontend Agent', 'Backend Agent', 'Security Agent'],
      ['Monitoring Agent', 'Self-Healing Agent', 'Rollback Agent'],
      ['Documentation Agent'],
      ['Frontend Code Agent', 'Backend Code Agent', 'Scaffolding Agent'],
    ];

    const nodes: any[] = [];
    const edges: any[] = [];
    let yOffset = 0;

    stages.forEach((stage, stageIdx) => {
      const stageWidth = stage.length * 160;
      const startX = -(stageWidth / 2) + 80;

      stage.forEach((agentName, agentIdx) => {
        const state = agentStates[agentName];
        const nodeId = agentName.replace(/ /g, '_');

        const nodeColor =
          state?.status === 'completed' ? '#22c55e' :
            state?.status === 'running' ? '#6366f1' :
              state?.status === 'failed' ? '#ef4444' : '#334155';

        nodes.push({
          id: nodeId,
          position: { x: startX + agentIdx * 170, y: yOffset },
          data: {
            label: (
              <div className="text-center">
                <div className="text-[11px] font-semibold text-white leading-tight">
                  {agentName.replace(' Agent', '')}
                </div>
                <div className={`text-[9px] mt-0.5 capitalize ${state?.status === 'completed' ? 'text-success-400' :
                    state?.status === 'running' ? 'text-brand-400' :
                      state?.status === 'failed' ? 'text-danger-400' : 'text-dark-500'
                  }`}>{state?.status || 'idle'}</div>
              </div>
            )
          },
          style: {
            background: `rgba(${state?.status === 'completed' ? '34,197,94' : state?.status === 'running' ? '99,102,241' : state?.status === 'failed' ? '239,68,68' : '30,41,59'},0.15)`,
            border: `1px solid ${nodeColor}40`,
            borderRadius: '12px',
            padding: '10px 14px',
            fontSize: '11px',
            minWidth: '130px',
            boxShadow: state?.status === 'running' ? `0 0 12px ${nodeColor}50` : 'none',
          },
        });

        // Add edges from previous stage
        if (stageIdx > 0) {
          stages[stageIdx - 1].forEach((prevAgent) => {
            edges.push({
              id: `${prevAgent}-${agentName}`,
              source: prevAgent.replace(/ /g, '_'),
              target: nodeId,
              style: { stroke: '#6366f150', strokeWidth: 1.5 },
              animated: state?.status === 'running',
            });
          });
        }
      });

      yOffset += 90;
    });

    return { nodes, edges };
  };

  const { nodes, edges } = buildFlowGraph();

  const completedCount = Object.values(agentStates).filter((a: any) => a.status === 'completed').length;
  const failedCount = Object.values(agentStates).filter((a: any) => a.status === 'failed').length;
  const runningCount = Object.values(agentStates).filter((a: any) => a.status === 'running').length;
  const progress = (completedCount / AGENT_SEQUENCE.length) * 100;
  const outputKeys = Object.keys(outputs).filter(k => k !== 'generated_files');

  // ── File browsing helpers ──────────────────────────────────────────────────
  const loadFileTree = async () => {
    if (!workflowId) return;
    try {
      const data = await api.get(`/artifacts/${workflowId}/files`, token);
      setFileTree(data.tree || []);
    } catch (e) {
      console.error('Failed to load file tree:', e);
    }
  };

  const loadFileContent = async (path: string) => {
    if (!workflowId) return;
    setFileContentLoading(true);
    setSelectedFile(path);
    setFileContent(null);
    try {
      const data = await api.get(`/artifacts/${workflowId}/files/${path}`, token);
      setFileContent(data.content || '');
    } catch (e) {
      setFileContent('// Error loading file');
    } finally {
      setFileContentLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!workflowId) return;
    setDownloadLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/artifacts/${workflowId}/download`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `buildflow-project-${workflowId?.slice(0, 8)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Download error:', e);
    } finally {
      setDownloadLoading(false);
    }
  };

  // Check if files exist when workflow is already completed on mount
  useEffect(() => {
    if (workflow?.outputs?.generated_files && !filesReady) {
      setFilesReady(true);
      loadFileTree();
    }
  }, [workflow?.outputs]);

  return (
    <div className="h-full flex flex-col">
      {/* Workflow Header */}
      <div className="px-6 py-4 border-b border-dark-800/60 flex items-center gap-4 flex-shrink-0">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-800/60 transition-colors"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="font-semibold text-white text-sm truncate">
              {workflow?.user_input?.slice(0, 80) || 'Loading...'}
            </h1>
            {workflow?.status && (
              <span className={`badge ${workflow.status === 'completed' ? 'badge-completed' :
                  workflow.status === 'running' ? 'badge-running' :
                    workflow.status === 'failed' ? 'badge-failed' : 'badge-pending'
                }`}>
                <div className="w-1.5 h-1.5 rounded-full bg-current" />
                {workflow.status}
              </span>
            )}
          </div>
          <div className="text-xs text-dark-500 font-mono mt-0.5">{workflowId}</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-dark-400">
            <span className="text-success-400 font-mono">{completedCount}</span>/{AGENT_SEQUENCE.length} agents
          </div>
          {failedCount > 0 && (
            <div className="text-xs text-danger-400 font-mono">{failedCount} failed</div>
          )}
          <button
            onClick={fetchWorkflow}
            className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-800/60 transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-6 py-2 flex-shrink-0">
        <div className="progress-track">
          <motion.div
            className="progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-xs text-dark-500">Workflow Progress</span>
          <span className="text-xs text-brand-400 font-mono">{Math.round(progress)}%</span>
        </div>
      </div>

      {/* Main split view */}
      <div className="flex-1 grid grid-cols-3 gap-0 overflow-hidden">
        {/* Left: Agent List + Terminal */}
        <div className="col-span-1 flex flex-col border-r border-dark-800/60 overflow-hidden">
          {/* Agent Status List */}
          <div className="flex-shrink-0 p-4 border-b border-dark-800/60">
            <h3 className="text-xs font-semibold text-dark-400 uppercase tracking-wider mb-3">Agent Execution</h3>
            <div className="space-y-1.5 max-h-64 overflow-y-auto">
              {AGENT_SEQUENCE.map((agentName) => {
                const state = agentStates[agentName];
                const isRunning = state?.status === 'running';
                const isDone = state?.status === 'completed';
                const isFailed = state?.status === 'failed';

                return (
                  <motion.div
                    key={agentName}
                    animate={isRunning ? { borderColor: ['rgba(99,102,241,0.2)', 'rgba(99,102,241,0.5)', 'rgba(99,102,241,0.2)'] } : {}}
                    transition={{ duration: 2, repeat: Infinity }}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition-all ${isRunning ? 'bg-brand-500/10 border border-brand-500/30' :
                        isDone ? 'bg-success-500/5 border border-success-500/15' :
                          isFailed ? 'bg-danger-500/10 border border-danger-500/20' :
                            'bg-dark-900/40 border border-transparent'
                      }`}
                  >
                    <div className={`flex-shrink-0 ${isRunning ? 'agent-dot agent-dot-running' :
                        isDone ? 'agent-dot agent-dot-completed' :
                          isFailed ? 'agent-dot agent-dot-failed' :
                            'agent-dot agent-dot-idle'
                      }`} />
                    <span className={`flex-1 ${isRunning ? 'text-brand-300' :
                        isDone ? 'text-success-400' :
                          isFailed ? 'text-danger-400' :
                            'text-dark-500'
                      }`}>{agentName}</span>
                    {isRunning && <RefreshCw size={10} className="text-brand-400 animate-spin-slow" />}
                    {isDone && <CheckCircle size={10} className="text-success-400" />}
                    {isFailed && <XCircle size={10} className="text-danger-400" />}
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Terminal */}
          <div className="flex-1 flex flex-col min-h-0 p-4">
            <div className="terminal flex-1 flex flex-col min-h-0">
              <div className="terminal-header">
                <div className="terminal-dot bg-danger-500" />
                <div className="terminal-dot bg-warning-500" />
                <div className="terminal-dot bg-success-500" />
                <span className="ml-2 text-dark-500 text-xs">workflow.log</span>
                <div className="ml-auto flex items-center gap-1.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-success-400 animate-pulse' : 'bg-dark-600'}`} />
                  <span className="text-[10px] text-dark-600">{wsConnected ? 'live' : 'connecting...'}</span>
                </div>
              </div>
              <div className="terminal-body flex-1 overflow-y-auto">
                <AnimatePresence initial={false}>
                  {workflowLogs.slice(0, 100).map((log, i) => (
                    <motion.div
                      key={log.id || i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="log-line"
                    >
                      <span className="log-time">
                        {new Date(log.timestamp * 1000).toLocaleTimeString('en', { hour12: false })}
                      </span>
                      <span className={`log-level-${log.level || 'info'}`}>
                        {log.message}
                      </span>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {workflowLogs.length === 0 && (
                  <div className="text-dark-600 text-xs py-4 typing-cursor">Waiting for agent events</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right: DAG Visualization + Outputs */}
        <div className="col-span-2 flex flex-col overflow-hidden">
          {/* DAG */}
          <div className="flex-1 min-h-0 relative" style={{ background: 'rgba(6,13,26,0.5)' }}>
            <div className="absolute top-3 left-3 z-10 text-xs text-dark-500 flex items-center gap-2">
              <Activity size={12} className="text-brand-400" />
              <span>Workflow DAG — Live Execution</span>
            </div>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              attributionPosition="bottom-right"
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#6366f110" gap={30} />
              <Controls className="!bg-dark-900 !border-dark-700" />
            </ReactFlow>
          </div>

          {/* Outputs + Files Panel */}
          {(outputKeys.length > 0 || filesReady) && (
            <div className="flex-shrink-0 border-t border-dark-800/60 max-h-80 overflow-hidden flex flex-col">
              {/* Tab Header */}
              <div className="flex items-center border-b border-dark-800/60 flex-shrink-0">
                <button
                  onClick={() => setActiveTab('outputs')}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                    activeTab === 'outputs'
                      ? 'border-brand-500 text-brand-300'
                      : 'border-transparent text-dark-400 hover:text-white'
                  }`}
                >
                  <Terminal size={12} />
                  Generated Outputs
                  {outputKeys.length > 0 && (
                    <span className="badge badge-completed">{outputKeys.length}</span>
                  )}
                </button>
                <button
                  onClick={() => { setActiveTab('files'); if (filesReady && fileTree.length === 0) loadFileTree(); }}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                    activeTab === 'files'
                      ? 'border-brand-500 text-brand-300'
                      : 'border-transparent text-dark-400 hover:text-white'
                  }`}
                >
                  <FileCode size={12} />
                  Generated Files
                  {filesReady && (
                    <span className="badge badge-completed">
                      {outputs?.generated_files?.count || fileTree.filter(f => f.type === 'file').length}
                    </span>
                  )}
                </button>
                {filesReady && (
                  <button
                    onClick={handleDownload}
                    disabled={downloadLoading}
                    className="ml-auto mr-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-brand-500/20 text-brand-300 border border-brand-500/30 hover:bg-brand-500/30 transition-all disabled:opacity-50"
                  >
                    {downloadLoading ? <RefreshCw size={11} className="animate-spin" /> : <Download size={11} />}
                    {downloadLoading ? 'Preparing...' : 'Download ZIP'}
                  </button>
                )}
              </div>

              {/* Outputs Tab */}
              {activeTab === 'outputs' && (
                <>
                  <div className="flex overflow-x-auto gap-2 p-3 border-b border-dark-800/40 flex-shrink-0">
                    {outputKeys.map((key) => (
                      <button
                        key={key}
                        onClick={() => setActiveOutput(activeOutput === key ? null : key)}
                        className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                          activeOutput === key
                            ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
                            : 'bg-dark-800/60 text-dark-400 border border-dark-700/60 hover:text-white'
                        }`}
                      >
                        {key.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>
                  {activeOutput && outputs[activeOutput] && (
                    <div className="flex-1 overflow-y-auto p-4">
                      <pre className="text-xs text-dark-300 font-mono whitespace-pre-wrap leading-relaxed">
                        {JSON.stringify(outputs[activeOutput], null, 2)}
                      </pre>
                    </div>
                  )}
                </>
              )}

              {/* Files Tab */}
              {activeTab === 'files' && (
                <div className="flex-1 flex overflow-hidden">
                  {/* File Tree */}
                  <div className="w-56 flex-shrink-0 border-r border-dark-800/60 overflow-y-auto py-2">
                    {fileTree.length === 0 ? (
                      <div className="flex items-center justify-center h-full">
                        <div className="text-xs text-dark-600 py-4 text-center px-3">
                          {filesReady ? 'Loading file tree...' : 'No files generated yet'}
                        </div>
                      </div>
                    ) : (
                      fileTree.map((entry, i) => (
                        <button
                          key={i}
                          onClick={() => entry.type === 'file' && loadFileContent(entry.path)}
                          className={`w-full flex items-center gap-2 px-3 py-1.5 text-left text-[11px] transition-colors ${
                            selectedFile === entry.path
                              ? 'bg-brand-500/15 text-brand-300'
                              : entry.type === 'directory'
                              ? 'text-dark-400 cursor-default'
                              : 'text-dark-400 hover:text-white hover:bg-dark-800/40'
                          }`}
                          style={{ paddingLeft: `${(entry.path.split('/').length) * 10 + 8}px` }}
                        >
                          {entry.type === 'directory' ? (
                            <FolderOpen size={11} className="text-brand-500/70 flex-shrink-0" />
                          ) : (
                            <FileCode size={11} className="text-dark-500 flex-shrink-0" />
                          )}
                          <span className="truncate">{entry.path.split('/').pop()}</span>
                          {entry.type === 'file' && entry.size && (
                            <span className="ml-auto text-[9px] text-dark-700 flex-shrink-0">
                              {entry.size > 1024 ? `${(entry.size / 1024).toFixed(1)}k` : `${entry.size}b`}
                            </span>
                          )}
                        </button>
                      ))
                    )}
                  </div>

                  {/* File Content Viewer */}
                  <div className="flex-1 overflow-y-auto">
                    {!selectedFile ? (
                      <div className="flex items-center justify-center h-full">
                        <div className="text-center">
                          <FileCode size={28} className="text-dark-700 mx-auto mb-2" />
                          <p className="text-xs text-dark-600">Select a file to view its contents</p>
                        </div>
                      </div>
                    ) : fileContentLoading ? (
                      <div className="flex items-center justify-center h-full">
                        <RefreshCw size={16} className="text-brand-400 animate-spin" />
                      </div>
                    ) : (
                      <div className="p-3">
                        <div className="text-[10px] text-dark-600 font-mono mb-2 px-1">{selectedFile}</div>
                        <pre className="text-[11px] text-dark-300 font-mono whitespace-pre-wrap leading-relaxed">
                          {fileContent}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
