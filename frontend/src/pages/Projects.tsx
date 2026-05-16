import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, Plus, Zap, Clock, ArrowRight, Trash2, BarChart3 } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { NewWorkflowModal } from '../components/workflow/NewWorkflowModal';
import { api } from '../services/api';

const PROJECT_TYPES = [
  { value: 'startup', label: '🚀 Startup Idea' },
  { value: 'saas', label: '☁️ SaaS Platform' },
  { value: 'hackathon', label: '🏆 Hackathon' },
  { value: 'college', label: '🎓 College Project' },
  { value: 'repo_analysis', label: '🔍 Repo Analysis' },
  { value: 'general', label: '📁 General' },
];

export function Projects() {
  const { projects, loadProjects, createProject, token } = useAppStore();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newType, setNewType] = useState('general');
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await createProject({ name: newName, description: newDesc, type: newType });
      setShowCreate(false);
      setNewName('');
      setNewDesc('');
      setNewType('general');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (projectId: string) => {
    try {
      await api.delete(`/projects/${projectId}`, token);
      loadProjects();
    } catch (e) {
      console.error('Delete failed:', e);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Projects</h1>
          <p className="text-dark-400 text-sm mt-1">{projects.length} workspace{projects.length !== 1 ? 's' : ''}</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6"
        >
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <FolderOpen size={16} className="text-brand-400" />
            Create New Project
          </h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-dark-400 mb-1.5 block">Project Name</label>
              <input
                className="input-field"
                placeholder="My AI-Powered Platform"
                value={newName}
                onChange={e => setNewName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-dark-400 mb-1.5 block">Description</label>
              <textarea
                className="textarea-field"
                rows={2}
                placeholder="Brief description of what you're building..."
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-dark-400 mb-1.5 block">Project Type</label>
              <div className="grid grid-cols-3 gap-2">
                {PROJECT_TYPES.map(pt => (
                  <button
                    key={pt.value}
                    onClick={() => setNewType(pt.value)}
                    className={`p-2.5 rounded-xl text-xs font-medium transition-all border ${
                      newType === pt.value
                        ? 'bg-brand-500/15 border-brand-500/40 text-brand-300'
                        : 'bg-dark-800/60 border-dark-700/60 text-dark-400 hover:text-white hover:border-dark-600'
                    }`}
                  >
                    {pt.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={handleCreate} disabled={creating} className="btn-primary flex-1 justify-center">
                {creating ? 'Creating...' : 'Create Project'}
              </button>
              <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Projects grid */}
      {projects.length === 0 ? (
        <div className="glass-card p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-dark-800 flex items-center justify-center mx-auto mb-4">
            <FolderOpen size={24} className="text-dark-600" />
          </div>
          <p className="text-dark-300 font-medium mb-2">No projects yet</p>
          <p className="text-dark-500 text-sm mb-6">Create a project to start orchestrating agents</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mx-auto">
            <Plus size={16} /> Create First Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project, i) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="glass-card p-5 group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-9 h-9 rounded-xl bg-brand-500/15 flex items-center justify-center">
                  <FolderOpen size={16} className="text-brand-400" />
                </div>
                <button
                  onClick={() => handleDelete(project.id)}
                  className="opacity-0 group-hover:opacity-100 text-dark-600 hover:text-danger-400 transition-all p-1"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <h3 className="font-semibold text-white mb-1 truncate">{project.name}</h3>
              <p className="text-xs text-dark-400 mb-3 line-clamp-2">{project.description || 'No description'}</p>

              <div className="flex items-center gap-2 mb-4">
                <span className="badge badge-pending capitalize">{project.type}</span>
                <span className="text-xs text-dark-600 flex items-center gap-1">
                  <Clock size={10} />
                  {new Date(project.created_at * 1000).toLocaleDateString()}
                </span>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setSelectedProject(project.id);
                    setShowWorkflow(true);
                  }}
                  className="btn-primary flex-1 justify-center text-xs py-2"
                >
                  <Zap size={12} /> Run Workflow
                </button>
                <button
                  onClick={() => navigate('/observability')}
                  className="btn-secondary px-3 py-2"
                >
                  <BarChart3 size={12} />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {showWorkflow && (
        <NewWorkflowModal
          projectId={selectedProject}
          onClose={() => setShowWorkflow(false)}
        />
      )}
    </div>
  );
}
