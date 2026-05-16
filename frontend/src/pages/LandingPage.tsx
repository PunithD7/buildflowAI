import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Zap, Shield, Activity, Code2, ChevronRight, Play, GitBranch, Lock, Cpu, Globe } from 'lucide-react';
import { useAppStore } from '../store/appStore';


const AGENT_NAMES = [
  'Goal Understanding', 'Planning', 'Research', 'Strategy',
  'Architecture', 'Tech Stack', 'Frontend', 'Backend',
  'Security', 'Documentation', 'Monitoring', 'Self-Healing', 'Rollback',
];

const features = [
  { icon: Cpu, title: 'Multi-Agent Orchestration', desc: '13 specialized AI agents working in harmony', color: 'brand' },
  { icon: Shield, title: 'Secure Execution', desc: 'TEE-inspired sandboxed agent execution', color: 'cyber' },
  { icon: Activity, title: 'Real-Time Observability', desc: 'Live workflow DAG with execution traces', color: 'success' },
  { icon: Lock, title: 'DDoS Protection', desc: 'Intelligent traffic filtering & rate limiting', color: 'warning' },
  { icon: GitBranch, title: 'Self-Healing', desc: 'Automatic failover & retry with backoff', color: 'brand' },
  { icon: Globe, title: 'Multi-Model AI', desc: 'Gemini, GPT-4o, Claude with smart routing', color: 'cyber' },
];

const examples = [
  'Build an AI-powered placement platform',
  'Create a traffic prediction SaaS',
  'Generate a social media analytics tool',
  'Analyze and improve this repository',
  'Design a multi-tenant CRM system',
  'Build an AI startup for student productivity',
];

export function LandingPage() {
  const { autoLogin, isAuthenticated } = useAppStore();
  const navigate = useNavigate();

  const handleGetStarted = async () => {
    await autoLogin();
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen cyber-bg overflow-x-hidden">
      {/* Animated orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <motion.div
          animate={{ x: [0, 30, 0], y: [0, -20, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-20 left-1/4 w-[500px] h-[500px] bg-brand-600/8 rounded-full blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -20, 0], y: [0, 30, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute bottom-20 right-1/4 w-[400px] h-[400px] bg-cyber-600/8 rounded-full blur-3xl"
        />
      </div>

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-dark-800/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-cyber-500 flex items-center justify-center shadow-glow">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-base gradient-text">BuildFlow Secure AI</div>
            <div className="text-[10px] text-dark-500 font-mono tracking-widest">AUTONOMOUS EXECUTION PLATFORM</div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-success-500/10 border border-success-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
            <span className="text-xs text-success-400 font-medium">System Operational</span>
          </div>
          <button onClick={handleGetStarted} className="btn-primary">
            <Play size={14} />
            Launch Platform
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 text-center px-8 pt-24 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 mb-8">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
            <span className="text-xs text-brand-300 font-medium font-mono">v1.0 — 13 Specialized AI Agents</span>
          </div>

          <h1 className="text-6xl md:text-7xl font-black mb-6 leading-tight">
            <span className="gradient-text">Transform Ideas</span>
            <br />
            <span className="text-white">into Execution</span>
          </h1>

          <p className="text-xl text-dark-300 max-w-2xl mx-auto mb-10 leading-relaxed">
            BuildFlow Secure AI autonomously understands your goals, plans workflows,
            generates architecture, and coordinates 13 specialized agents — all in real-time.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap">
            <button onClick={handleGetStarted} className="btn-primary text-base px-8 py-4">
              <Zap size={18} />
              Start Building Now
              <ChevronRight size={16} />
            </button>
            <button
              onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}
              className="btn-secondary text-base px-8 py-4"
            >
              See Demo
            </button>
            <button
              onClick={() => navigate('/gitrepo')}
              className="btn-secondary text-base px-8 py-4 border border-cyber-500/40 hover:border-cyber-400 hover:bg-cyber-500/10"
            >
              <GitBranch size={18} />
              Analyze Git Repo
            </button>
          </div>
        </motion.div>

        {/* Agent carousel */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="mt-16 overflow-hidden"
        >
          <div className="flex gap-3 animate-[scroll_20s_linear_infinite]" style={{ width: 'max-content' }}>
            {[...AGENT_NAMES, ...AGENT_NAMES].map((name, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-4 py-2 glass rounded-full text-sm text-dark-300 whitespace-nowrap"
              >
                <div className="w-2 h-2 rounded-full bg-brand-500 animate-pulse-slow" />
                {name} Agent
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section className="relative z-10 px-8 py-16 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl font-bold text-white mb-4">Platform Capabilities</h2>
          <p className="text-dark-400">Production-grade infrastructure for autonomous AI execution</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="glass-card p-6"
            >
              <div className={`w-10 h-10 rounded-xl mb-4 flex items-center justify-center ${feat.color === 'brand' ? 'bg-brand-500/20 text-brand-400' :
                feat.color === 'cyber' ? 'bg-cyber-500/20 text-cyber-400' :
                  feat.color === 'success' ? 'bg-success-500/20 text-success-400' :
                    'bg-warning-500/20 text-warning-400'
                }`}>
                <feat.icon size={20} />
              </div>
              <h3 className="font-semibold text-white mb-2">{feat.title}</h3>
              <p className="text-sm text-dark-400">{feat.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Example inputs */}
      <section id="demo" className="relative z-10 px-8 py-16 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-10"
        >
          <h2 className="text-3xl font-bold text-white mb-4">What can you build?</h2>
          <p className="text-dark-400">Input any idea — BuildFlow handles the rest autonomously</p>
        </motion.div>

        <div className="space-y-3">
          {examples.map((example, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              whileHover={{ x: 6 }}
              onClick={handleGetStarted}
              className="flex items-center gap-4 p-4 glass rounded-xl cursor-pointer border border-dark-700/60 hover:border-brand-500/30 group transition-all"
            >
              <div className="w-8 h-8 rounded-lg bg-brand-500/15 flex items-center justify-center flex-shrink-0">
                <Code2 size={14} className="text-brand-400" />
              </div>
              <span className="text-dark-200 group-hover:text-white transition-colors text-sm">{example}</span>
              <ChevronRight size={14} className="ml-auto text-dark-600 group-hover:text-brand-400 transition-colors" />
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mt-12"
        >
          <button onClick={handleGetStarted} className="btn-primary text-base px-10 py-4">
            <Zap size={18} />
            Open BuildFlow Secure AI
          </button>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 text-center py-8 border-t border-dark-800/50">
        <p className="text-dark-600 text-sm font-mono">
          BuildFlow Secure AI — Autonomous Multi-Agent Platform · v1.0.0
        </p>
      </footer>

      <style>{`
        @keyframes scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}
