import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, FolderOpen, Activity, Shield, Clock, TrendingUp, Plus, ArrowRight, Cpu } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { api } from '../services/api';
import { NewWorkflowModal } from '../components/workflow/NewWorkflowModal';

const STAT_CARDS = [
  { label: 'Active Agents', value: '13', icon: Cpu, color: 'brand', suffix: 'ready' },
  { label: 'Workflows Run', value: '0', icon: Zap, color: 'cyber', suffix: 'total' },
  { label: 'Success Rate', value: '98.2%', icon: TrendingUp, color: 'success', suffix: 'avg' },
  { label: 'Avg. Completion', value: '~3m', icon: Clock, color: 'warning', suffix: 'time' },
];

const QUICK_PROMPTS = [
  { label: 'AI SaaS Platform', prompt: 'Build an AI-powered SaaS platform for automating content creation and marketing workflows' },
  { label: 'E-commerce Engine', prompt: 'Create a scalable e-commerce platform with AI-powered recommendations and inventory management' },
  { label: 'Student Productivity', prompt: 'Build an AI startup for student productivity with smart scheduling, note-taking, and exam preparation' },
  { label: 'Traffic Prediction', prompt: 'Create an AI traffic prediction system for smart city infrastructure with real-time monitoring' },
];

export function Dashboard() {
  const { projects, workflows, loadProjects, loadWorkflows, token } = useAppStore();
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [showNewWorkflow, setShowNewWorkflow] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
    loadWorkflows();
    fetchSystemStatus();
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const data = await api.get('/observability/dashboard', token);
      setSystemStatus(data);
    } catch (e) {}
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Mission Control</h1>
          <p className="text-dark-400 text-sm mt-1">BuildFlow Secure AI — Autonomous Execution Platform</p>
        </div>
        <button
          onClick={() => setShowNewWorkflow(true)}
          className="btn-primary"
        >
          <Plus size={16} />
          New Workflow
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="metric-card"
          >
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
              stat.color === 'brand' ? 'bg-brand-500/20 text-brand-400' :
              stat.color === 'cyber' ? 'bg-cyber-500/20 text-cyber-400' :
              stat.color === 'success' ? 'bg-success-500/20 text-success-400' :
              'bg-warning-500/20 text-warning-400'
            }`}>
              <stat.icon size={18} />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{stat.value}</div>
              <div className="text-xs text-dark-500">{stat.label} · {stat.suffix}</div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Start */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2 glass-card p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Zap size={16} className="text-brand-400" />
              Quick Launch
            </h2>
            <span className="text-xs text-dark-500">Select a prompt or type your own</span>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-5">
            {QUICK_PROMPTS.map((qp) => (
              <motion.button
                key={qp.label}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  setSelectedPrompt(qp.prompt);
                  setShowNewWorkflow(true);
                }}
                className="text-left p-4 rounded-xl bg-dark-900/60 border border-dark-700/60 hover:border-brand-500/30 hover:bg-dark-800/60 transition-all group"
              >
                <div className="text-sm font-medium text-dark-200 group-hover:text-white mb-1">{qp.label}</div>
                <div className="text-xs text-dark-500 line-clamp-2">{qp.prompt}</div>
              </motion.button>
            ))}
          </div>

          <button
            onClick={() => { setSelectedPrompt(''); setShowNewWorkflow(true); }}
            className="w-full btn-primary justify-center py-3"
          >
            <Zap size={16} />
            Launch Custom Workflow
          </button>
        </motion.div>

        {/* System Status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6"
        >
          <h2 className="font-semibold text-white flex items-center gap-2 mb-5">
            <Activity size={16} className="text-cyber-400" />
            System Status
          </h2>

          <div className="space-y-3">
            {[
              { label: 'API Service', status: 'operational', color: 'success' },
              { label: 'Agent Orchestrator', status: 'ready', color: 'success' },
              { label: 'Rate Limiter', status: 'active', color: 'brand' },
              { label: 'DDoS Protection', status: 'active', color: 'brand' },
              { label: 'TEE Execution', status: 'sandboxed', color: 'cyber' },
              { label: 'WebSocket Hub', status: 'listening', color: 'success' },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between">
                <span className="text-sm text-dark-300">{item.label}</span>
                <div className={`flex items-center gap-1.5 ${
                  item.color === 'success' ? 'text-success-400' :
                  item.color === 'brand' ? 'text-brand-400' :
                  'text-cyber-400'
                }`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    item.color === 'success' ? 'bg-success-400' :
                    item.color === 'brand' ? 'bg-brand-400' :
                    'bg-cyber-400'
                  } animate-pulse`} />
                  <span className="text-xs font-medium">{item.status}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-dark-800">
            <div className="text-xs text-dark-500 mb-2">Security Layer</div>
            <div className="flex gap-2 flex-wrap">
              <span className="badge badge-running">Rate Limit</span>
              <span className="badge badge-running">DDoS Guard</span>
              <span className="badge badge-completed">JWT Auth</span>
              <span className="badge badge-completed">RBAC</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recent Workflows */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="glass-card p-6"
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <FolderOpen size={16} className="text-brand-400" />
            Recent Workflows
          </h2>
          <button
            onClick={() => navigate('/projects')}
            className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
          >
            View all <ArrowRight size={12} />
          </button>
        </div>

        {workflows.length === 0 ? (
          <div className="text-center py-10">
            <div className="w-12 h-12 rounded-2xl bg-dark-800 flex items-center justify-center mx-auto mb-4">
              <Zap size={20} className="text-dark-600" />
            </div>
            <p className="text-dark-400 text-sm">No workflows yet</p>
            <p className="text-dark-600 text-xs mt-1">Launch your first workflow above</p>
          </div>
        ) : (
          <div className="space-y-3">
            {workflows.slice(0, 5).map((wf) => (
              <div
                key={wf.workflow_id}
                onClick={() => navigate(`/workflow/${wf.workflow_id}`)}
                className="flex items-center gap-4 p-4 rounded-xl bg-dark-900/40 border border-dark-800/60 hover:border-brand-500/20 cursor-pointer transition-all group"
              >
                <div className={`flex-shrink-0 ${
                  wf.status === 'completed' ? 'badge-completed' :
                  wf.status === 'running' ? 'badge-running' :
                  wf.status === 'failed' ? 'badge-failed' : 'badge-pending'
                } badge`}>
                  <div className="w-1.5 h-1.5 rounded-full bg-current" />
                  {wf.status}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-dark-200 group-hover:text-white truncate">{wf.user_input}</p>
                  <p className="text-xs text-dark-600 mt-0.5">{wf.workflow_id.slice(0, 8)}... · {new Date(wf.created_at * 1000).toLocaleString()}</p>
                </div>
                <ArrowRight size={14} className="text-dark-600 group-hover:text-brand-400 transition-colors flex-shrink-0" />
              </div>
            ))}
          </div>
        )}
      </motion.div>

      {showNewWorkflow && (
        <NewWorkflowModal
          onClose={() => setShowNewWorkflow(false)}
          initialPrompt={selectedPrompt}
        />
      )}
    </div>
  );
}
