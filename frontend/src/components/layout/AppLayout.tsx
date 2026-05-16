import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, FolderOpen, Activity, Shield, FileText,
  ChevronLeft, ChevronRight, Zap, LogOut, Settings,
  Bell, Search, User, Cpu, Globe
} from 'lucide-react';
import { useAppStore } from '../../store/appStore';
import { useState, useEffect } from 'react';
import { createSystemWebSocket } from '../../services/api';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/projects', icon: FolderOpen, label: 'Projects' },
  { path: '/observability', icon: Activity, label: 'Observability' },
  { path: '/security', icon: Shield, label: 'Security' },
  { path: '/documents', icon: FileText, label: 'Documents' },
];

export function AppLayout() {
  const { sidebarCollapsed, setSidebarCollapsed, user, logout, addSecurityEvent, addLog } = useAppStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState(0);
  const [systemStatus, setSystemStatus] = useState('operational');

  // Connect to system WebSocket for global events
  useEffect(() => {
    let ws: WebSocket;
    let retryTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        ws = createSystemWebSocket((data) => {
          if (data.type === 'security_event') {
            addSecurityEvent(data);
            setNotifications(n => n + 1);
          } else if (data.type === 'log') {
            addLog(data);
          }
        });
      } catch (e) {
        retryTimeout = setTimeout(connect, 5000);
      }
    };

    connect();

    return () => {
      ws?.close();
      clearTimeout(retryTimeout);
    };
  }, [addSecurityEvent, addLog]);

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <div className="flex h-screen cyber-bg overflow-hidden">
      {/* Animated background gradient */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-600/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyber-600/5 rounded-full blur-3xl" />
      </div>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarCollapsed ? 68 : 240 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="relative flex flex-col h-full z-20 flex-shrink-0"
        style={{
          background: 'rgba(6, 13, 26, 0.95)',
          borderRight: '1px solid rgba(99, 102, 241, 0.15)',
          backdropFilter: 'blur(20px)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-dark-800/80">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-cyber-500 flex items-center justify-center glow-brand">
            <Zap size={16} className="text-white" />
          </div>
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="font-bold text-sm gradient-text leading-tight">BuildFlow</div>
                <div className="text-[10px] text-dark-500 font-mono">SECURE AI v1.0</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = isActive(item.path);
            return (
              <motion.button
                key={item.path}
                onClick={() => navigate(item.path)}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.98 }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                  active
                    ? 'text-brand-300 bg-brand-500/10 border border-brand-500/20 shadow-glow-sm'
                    : 'text-dark-400 hover:text-white hover:bg-dark-800/60'
                }`}
                title={sidebarCollapsed ? item.label : undefined}
              >
                <item.icon
                  size={18}
                  className={active ? 'text-brand-400' : 'text-dark-500'}
                />
                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="font-medium"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {active && !sidebarCollapsed && (
                  <motion.div
                    className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-400"
                    layoutId="nav-indicator"
                  />
                )}
              </motion.button>
            );
          })}
        </nav>

        {/* System Status */}
        {!sidebarCollapsed && (
          <div className="px-3 py-2 mx-2 mb-2 rounded-lg bg-dark-900/60 border border-dark-800">
            <div className="flex items-center gap-2">
              <div className={`agent-dot ${systemStatus === 'operational' ? 'agent-dot-completed' : 'agent-dot-failed'}`} />
              <span className="text-xs text-dark-400 font-mono">System {systemStatus}</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Cpu size={10} className="text-dark-600" />
              <span className="text-[10px] text-dark-600 font-mono">16 agents ready</span>
            </div>
          </div>
        )}

        {/* User section */}
        <div className="p-2 border-t border-dark-800/80">
          <div className={`flex items-center gap-3 px-2 py-2 rounded-xl ${sidebarCollapsed ? 'justify-center' : ''}`}>
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-cyber-600 flex items-center justify-center">
              <User size={12} className="text-white" />
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 min-w-0"
                >
                  <div className="text-xs font-semibold text-dark-200 truncate">{user?.name || 'Demo User'}</div>
                  <div className="text-[10px] text-dark-500 truncate">{user?.role || 'developer'}</div>
                </motion.div>
              )}
            </AnimatePresence>
            {!sidebarCollapsed && (
              <button onClick={logout} className="text-dark-600 hover:text-danger-400 transition-colors">
                <LogOut size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-dark-800 border border-dark-700 flex items-center justify-center text-dark-400 hover:text-white hover:border-brand-500/50 transition-all z-10"
        >
          {sidebarCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      </motion.aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header
          className="h-14 flex items-center justify-between px-6 flex-shrink-0 z-10"
          style={{
            background: 'rgba(6, 13, 26, 0.8)',
            borderBottom: '1px solid rgba(99, 102, 241, 0.1)',
            backdropFilter: 'blur(20px)',
          }}
        >
          <div className="flex items-center gap-3 flex-1">
            <div className="relative max-w-sm flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-500" />
              <input
                type="text"
                placeholder="Search projects, workflows..."
                className="w-full bg-dark-900/60 border border-dark-700/60 rounded-lg pl-9 pr-4 py-1.5 text-sm text-dark-200 placeholder-dark-600 focus:outline-none focus:border-brand-500/40 transition-colors"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Status pills */}
            <div className="hidden md:flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-success-500/10 border border-success-500/20">
                <div className="agent-dot agent-dot-completed w-1.5 h-1.5" />
                <span className="text-[11px] text-success-400 font-medium">API Live</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/20">
                <Globe size={10} className="text-brand-400" />
                <span className="text-[11px] text-brand-400 font-medium">16 Agents</span>
              </div>
            </div>

            {/* Notifications */}
            <button
              onClick={() => setNotifications(0)}
              className="relative p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-800/60 transition-colors"
            >
              <Bell size={16} />
              {notifications > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-danger-500 text-[9px] font-bold text-white flex items-center justify-center">
                  {notifications > 9 ? '9+' : notifications}
                </span>
              )}
            </button>

            <button className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-800/60 transition-colors">
              <Settings size={16} />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
