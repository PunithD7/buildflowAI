import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, X, Cpu, ChevronRight, AlertCircle } from 'lucide-react';
import { useAppStore } from '../../store/appStore';

const EXAMPLE_PROMPTS = [
  'Build an AI-powered placement platform for college students with smart matching and interview prep',
  'Create a real-time traffic prediction system for smart cities using ML and sensor data',
  'Design a multi-tenant SaaS CRM with AI automation and analytics dashboard',
  'Build an AI startup for student productivity with scheduling, notes, and exam preparation',
  'Analyze and refactor this repository with security hardening and test coverage',
  'Create a social commerce platform with AI recommendations and creator tools',
];

interface Props {
  onClose: () => void;
  projectId?: string;
  initialPrompt?: string;
}

export function NewWorkflowModal({ onClose, projectId, initialPrompt = '' }: Props) {
  const { projects, startWorkflow, createProject } = useAppStore();
  const [userInput, setUserInput] = useState(initialPrompt);
  const [selectedProject, setSelectedProject] = useState(projectId || (projects[0]?.id || ''));
  const [creatingProject, setCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleStart = async () => {
    if (!userInput.trim()) {
      setError('Please describe what you want to build');
      return;
    }

    let targetProjectId = selectedProject;

    // Auto-create project if none exists
    if (!targetProjectId) {
      try {
        setLoading(true);
        const project = await createProject({
          name: newProjectName || 'My Project',
          description: userInput.slice(0, 100),
          type: 'general',
        });
        targetProjectId = project.id;
      } catch (e) {
        setError('Failed to create project');
        setLoading(false);
        return;
      }
    }

    try {
      setLoading(true);
      setError('');
      const workflow = await startWorkflow(targetProjectId, userInput);
      onClose();
      navigate(`/workflow/${workflow.workflow_id}`);
    } catch (e) {
      setError(`Failed to start workflow: ${e}`);
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="w-full max-w-2xl glass-card p-6"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-cyber-500 flex items-center justify-center shadow-glow">
                <Zap size={16} className="text-white" />
              </div>
              <div>
                <h2 className="font-bold text-white">Launch Workflow</h2>
                <p className="text-xs text-dark-400">16 agents · Full orchestration + Code Generation</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-800/60 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Project selector */}
          {projects.length > 0 && (
            <div className="mb-5">
              <label className="text-xs text-dark-400 mb-2 block">Project Workspace</label>
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="input-field"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} style={{ background: '#0f172a' }}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Main input */}
          <div className="mb-4">
            <label className="text-xs text-dark-400 mb-2 block">What do you want to build?</label>
            <textarea
              className="textarea-field text-base"
              rows={4}
              placeholder="Describe your idea, project, or problem statement in detail..."
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              autoFocus
            />
            <div className="flex justify-between mt-1">
              <span className="text-xs text-dark-600">Be specific for better agent outputs</span>
              <span className={`text-xs font-mono ${userInput.length > 500 ? 'text-warning-400' : 'text-dark-600'}`}>
                {userInput.length} chars
              </span>
            </div>
          </div>

          {/* Example prompts */}
          <div className="mb-5">
            <div className="text-xs text-dark-500 mb-2">Quick examples</div>
            <div className="flex gap-2 flex-wrap">
              {EXAMPLE_PROMPTS.slice(0, 3).map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setUserInput(prompt)}
                  className="text-xs px-3 py-1.5 rounded-full bg-dark-800/60 border border-dark-700/60 text-dark-400 hover:text-white hover:border-brand-500/30 transition-all truncate max-w-xs"
                >
                  {prompt.slice(0, 45)}...
                </button>
              ))}
            </div>
          </div>

          {/* Agent overview */}
          <div className="mb-5 p-4 rounded-xl bg-dark-900/40 border border-dark-800/60">
            <div className="flex items-center gap-2 mb-3">
              <Cpu size={12} className="text-brand-400" />
              <span className="text-xs text-dark-400">Agents that will run</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {['Goal Understanding', 'Planning', 'Research', 'Strategy', 'Architecture',
                'Tech Stack', 'Frontend', 'Backend', 'Security', 'Documentation',
                'Monitoring', 'Self-Healing', 'Rollback'].map((agent) => (
                <span key={agent} className="text-[10px] px-2 py-1 rounded-full bg-brand-500/8 border border-brand-500/15 text-brand-400">
                  {agent}
                </span>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-danger-500/10 border border-danger-500/20 mb-4">
              <AlertCircle size={14} className="text-danger-400 flex-shrink-0" />
              <p className="text-sm text-danger-300">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleStart}
              disabled={loading || !userInput.trim()}
              className="btn-primary flex-1 justify-center py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Starting agents...
                </>
              ) : (
                <>
                  <Zap size={16} />
                  Launch 16 Agents
                  <ChevronRight size={14} />
                </>
              )}
            </button>
            <button onClick={onClose} className="btn-secondary px-6">
              Cancel
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
