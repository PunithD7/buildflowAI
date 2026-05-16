import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Activity, Cpu, Globe, AlertTriangle, Server, RefreshCw, TrendingUp, Clock } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { api } from '../services/api';

export function Observability() {
  const { logs, agentEvents, token } = useAppStore();
  const [dashboard, setDashboard] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [dash, metr] = await Promise.all([
        api.get('/observability/dashboard', token),
        api.get('/observability/metrics', token),
      ]);
      setDashboard(dash);
      setMetrics(metr);
    } catch (e) {
      console.error('Observability fetch failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Observability Center</h1>
          <p className="text-dark-400 text-sm mt-1">Real-time execution monitoring & system telemetry</p>
        </div>
        <button onClick={fetchData} className="btn-secondary">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Agents', value: dashboard?.agents?.active_workflows || 0, icon: Cpu, color: 'brand', sub: 'running' },
          { label: 'WS Connections', value: dashboard?.websocket?.connections || 0, icon: Globe, color: 'cyber', sub: 'live' },
          { label: 'Blocked Requests', value: dashboard?.security?.total_blocked || 0, icon: AlertTriangle, color: 'danger', sub: 'total' },
          { label: 'Security Alerts', value: dashboard?.security?.total_alerts || 0, icon: Activity, color: 'warning', sub: 'events' },
        ].map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="metric-card"
          >
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
              m.color === 'brand' ? 'bg-brand-500/20 text-brand-400' :
              m.color === 'cyber' ? 'bg-cyber-500/20 text-cyber-400' :
              m.color === 'danger' ? 'bg-danger-500/20 text-danger-400' :
              'bg-warning-500/20 text-warning-400'
            }`}>
              <m.icon size={18} />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{m.value}</div>
              <div className="text-xs text-dark-500">{m.label} · {m.sub}</div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System metrics */}
        {metrics && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
          >
            <h2 className="font-semibold text-white mb-5 flex items-center gap-2">
              <Server size={16} className="text-brand-400" />
              System Resources
            </h2>
            <div className="space-y-4">
              {[
                { label: 'CPU Usage', value: metrics.cpu?.percent || 0, color: 'brand' },
                { label: 'Memory Usage', value: metrics.memory?.percent || 0, color: 'cyber' },
                { label: 'Disk Usage', value: metrics.disk?.percent || 0, color: 'warning' },
              ].map((resource) => (
                <div key={resource.label}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-dark-300">{resource.label}</span>
                    <span className={`font-mono ${
                      resource.value > 80 ? 'text-danger-400' :
                      resource.value > 60 ? 'text-warning-400' : 'text-success-400'
                    }`}>{resource.value.toFixed(1)}%</span>
                  </div>
                  <div className="progress-track">
                    <motion.div
                      className="progress-fill"
                      initial={{ width: 0 }}
                      animate={{ width: `${resource.value}%` }}
                      style={{
                        background: resource.value > 80
                          ? 'linear-gradient(90deg, #ef4444, #f87171)'
                          : resource.value > 60
                          ? 'linear-gradient(90deg, #f97316, #fb923c)'
                          : 'linear-gradient(90deg, #6366f1, #14b8a6)'
                      }}
                    />
                  </div>
                </div>
              ))}

              {metrics.memory && (
                <div className="pt-3 border-t border-dark-800 grid grid-cols-3 gap-3">
                  {[
                    { label: 'Total RAM', value: `${metrics.memory.total_gb}GB` },
                    { label: 'Used', value: `${metrics.memory.used_gb}GB` },
                    { label: 'Free', value: `${(metrics.memory.total_gb - metrics.memory.used_gb).toFixed(1)}GB` },
                  ].map(m => (
                    <div key={m.label} className="text-center">
                      <div className="text-sm font-bold text-white font-mono">{m.value}</div>
                      <div className="text-xs text-dark-500">{m.label}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Infrastructure Status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-6"
        >
          <h2 className="font-semibold text-white mb-5 flex items-center gap-2">
            <Activity size={16} className="text-cyber-400" />
            Infrastructure
          </h2>
          <div className="space-y-3">
            {[
              { name: 'FastAPI Backend', status: 'operational', latency: '< 5ms' },
              { name: 'Agent Orchestrator', status: 'operational', latency: 'async' },
              { name: 'WebSocket Server', status: 'operational', latency: 'realtime' },
              { name: 'Redis Cache', status: dashboard?.infrastructure?.redis === 'connected' ? 'connected' : 'fallback', latency: '< 1ms' },
              { name: 'Rate Limiter', status: 'active', latency: '< 1ms' },
              { name: 'DDoS Protection', status: 'active', latency: '< 1ms' },
            ].map((svc) => (
              <div key={svc.name} className="flex items-center gap-3 p-3 rounded-xl bg-dark-900/40 border border-dark-800/60">
                <div className={`agent-dot ${
                  svc.status === 'operational' || svc.status === 'active' || svc.status === 'connected'
                    ? 'agent-dot-completed' : 'agent-dot-running'
                }`} />
                <div className="flex-1">
                  <div className="text-sm text-dark-200">{svc.name}</div>
                  <div className="text-xs text-dark-500 capitalize">{svc.status}</div>
                </div>
                <div className="text-xs font-mono text-dark-500">{svc.latency}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Live Logs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <Clock size={16} className="text-brand-400" />
            Recent Execution Logs
          </h2>
          <span className="badge badge-running">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
            Live
          </span>
        </div>

        <div className="terminal">
          <div className="terminal-header">
            <div className="terminal-dot bg-danger-500" />
            <div className="terminal-dot bg-warning-500" />
            <div className="terminal-dot bg-success-500" />
            <span className="ml-2 text-dark-500 text-xs">system.log</span>
          </div>
          <div className="terminal-body" style={{ maxHeight: '300px' }}>
            {logs.slice(0, 50).map((log, i) => (
              <div key={log.id || i} className="log-line">
                <span className="log-time">
                  {new Date(log.timestamp * 1000).toLocaleTimeString('en', { hour12: false })}
                </span>
                <span className={`log-level-${log.level}`}>{log.message}</span>
              </div>
            ))}
            {logs.length === 0 && (
              <div className="text-dark-600 text-xs py-4">No logs yet — start a workflow to see execution traces</div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
