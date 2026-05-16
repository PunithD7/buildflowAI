import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Shield, AlertTriangle, Ban, Zap, Lock, RefreshCw, Play, CheckCircle } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { api } from '../services/api';

export function SecurityDashboard() {
  const { securityEvents, token } = useAppStore();
  const [ddosStats, setDdosStats] = useState<any>(null);
  const [rateLimitStatus, setRateLimitStatus] = useState<any>(null);
  const [teeStatus, setTeeStatus] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  useEffect(() => {
    fetchSecurityData();
    const interval = setInterval(fetchSecurityData, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchSecurityData = async () => {
    try {
      const [ddos, rl, tee] = await Promise.all([
        api.get('/security/ddos/stats', token),
        api.get('/security/rate-limits/status', token),
        api.get('/security/tee/status', token),
      ]);
      setDdosStats(ddos);
      setRateLimitStatus(rl);
      setTeeStatus(tee);
    } catch (e) {}
  };

  const handleSimulateDDoS = async () => {
    setSimulating(true);
    setSimResult(null);
    try {
      const result = await api.post('/security/ddos/simulate', {
        attacker_ip: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
        requests: 250,
      }, token);
      setSimResult(result);
      await fetchSecurityData();
    } catch (e) {
      console.error('Simulation failed:', e);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Security Dashboard</h1>
          <p className="text-dark-400 text-sm mt-1">DDoS protection · Rate limiting · TEE execution · RBAC</p>
        </div>
        <button onClick={fetchSecurityData} className="btn-secondary">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Security overview cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active IP Bans', value: ddosStats?.active_bans || 0, icon: Ban, color: 'danger', sub: 'DDoS' },
          { label: 'Total Blocked', value: ddosStats?.total_blocked || 0, icon: Shield, color: 'brand', sub: 'requests' },
          { label: 'Security Alerts', value: ddosStats?.total_alerts || 0, icon: AlertTriangle, color: 'warning', sub: 'total' },
          { label: 'Sandbox Executions', value: teeStatus?.active_sandboxes || 0, icon: Lock, color: 'cyber', sub: 'active' },
        ].map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="metric-card"
          >
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
              card.color === 'brand' ? 'bg-brand-500/20 text-brand-400' :
              card.color === 'cyber' ? 'bg-cyber-500/20 text-cyber-400' :
              card.color === 'danger' ? 'bg-danger-500/20 text-danger-400' :
              'bg-warning-500/20 text-warning-400'
            }`}>
              <card.icon size={18} />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{card.value}</div>
              <div className="text-xs text-dark-500">{card.label} · {card.sub}</div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DDoS Protection Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Shield size={16} className="text-danger-400" />
              DDoS Protection
            </h2>
            <span className="badge badge-completed">
              <div className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
              Active
            </span>
          </div>

          <div className="space-y-3 mb-5">
            {[
              { label: 'Detection Mode', value: 'Sliding Window (1s)' },
              { label: 'Threshold', value: `${ddosStats?.threshold_per_second || 100} req/s` },
              { label: 'Ban Duration', value: '1 hour (escalating)' },
              { label: 'Whitelisted IPs', value: (ddosStats?.whitelist || ['127.0.0.1']).join(', ') },
              { label: 'Suspicious IPs', value: ddosStats?.suspicious_ips?.length || 0 },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between text-sm">
                <span className="text-dark-400">{item.label}</span>
                <span className="text-dark-200 font-mono text-xs">{item.value}</span>
              </div>
            ))}
          </div>

          {/* Banned IPs */}
          {ddosStats?.banned_ips?.length > 0 && (
            <div className="mb-4">
              <div className="text-xs text-dark-500 mb-2">Currently Banned IPs</div>
              <div className="space-y-1">
                {ddosStats.banned_ips.slice(0, 5).map((ip: string) => (
                  <div key={ip} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-danger-500/10 border border-danger-500/20">
                    <Ban size={10} className="text-danger-400" />
                    <span className="text-xs font-mono text-danger-300">{ip}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Simulate attack */}
          <div className="pt-4 border-t border-dark-800">
            <div className="text-xs text-dark-500 mb-3">🧪 Attack Simulation Mode</div>
            <button
              onClick={handleSimulateDDoS}
              disabled={simulating}
              className="btn-danger w-full justify-center"
            >
              {simulating ? (
                <><RefreshCw size={14} className="animate-spin" /> Simulating...</>
              ) : (
                <><Play size={14} /> Simulate DDoS Attack</>
              )}
            </button>
            {simResult && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 p-3 rounded-xl bg-warning-500/10 border border-warning-500/20"
              >
                <div className="text-xs text-warning-300 font-medium mb-1">⚡ Attack Simulated</div>
                <div className="text-xs text-dark-400 font-mono">
                  IP: {simResult.simulation?.attacker_ip}<br />
                  Requests: {simResult.simulation?.requests_simulated}<br />
                  Status: {simResult.simulation?.status}
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Rate Limiting & TEE */}
        <div className="space-y-5">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-5"
          >
            <h2 className="font-semibold text-white flex items-center gap-2 mb-4">
              <Zap size={16} className="text-warning-400" />
              Rate Limiting
            </h2>
            <div className="space-y-2">
              {rateLimitStatus?.limits && Object.entries(rateLimitStatus.limits).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-dark-400 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-brand-300 font-mono text-xs">{String(val)}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-dark-800">
              <div className="text-xs text-dark-500 mb-2">Features</div>
              <div className="flex flex-wrap gap-1.5">
                {rateLimitStatus?.protection_features?.map((f: string) => (
                  <span key={f} className="text-[10px] px-2 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-5"
          >
            <h2 className="font-semibold text-white flex items-center gap-2 mb-4">
              <Lock size={16} className="text-cyber-400" />
              TEE-Inspired Execution
            </h2>
            <div className="space-y-2">
              {teeStatus?.features && Object.entries(teeStatus.features).map(([key, val]) => (
                <div key={key} className="flex items-center gap-2 text-sm">
                  <CheckCircle size={12} className={val ? 'text-success-400' : 'text-dark-600'} />
                  <span className="text-dark-300 capitalize">{key.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-dark-800">
              <p className="text-xs text-dark-500">{teeStatus?.note}</p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Security Events Feed */}
      {securityEvents.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6"
        >
          <h2 className="font-semibold text-white flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-warning-400" />
            Security Event Feed
          </h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {securityEvents.slice(0, 20).map((evt, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-warning-500/5 border border-warning-500/15 text-xs">
                <AlertTriangle size={12} className="text-warning-400 flex-shrink-0" />
                <span className="text-dark-300 font-medium capitalize">{evt.event}</span>
                <span className="text-dark-500">{JSON.stringify(evt.details).slice(0, 80)}</span>
                <span className="ml-auto text-dark-600 flex-shrink-0 font-mono">
                  {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
