import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';

import { useAppStore } from './store/appStore';

import { AppLayout } from './components/layout/AppLayout';

import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { WorkflowExecution } from './pages/WorkflowExecution';
import { Observability } from './pages/Observability';
import { SecurityDashboard } from './pages/SecurityDashboard';
import { DocumentsPage } from './pages/DocumentsPage';
import { LandingPage } from './pages/LandingPage';

import './index.css';
import GitRepo from './pages/gitrepo';
function App() {
  const { autoLogin } = useAppStore();

  useEffect(() => {
    autoLogin();
  }, [autoLogin]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route
            path="/workflow/:workflowId"
            element={<WorkflowExecution />}
          />
          <Route
            path="/observability"
            element={<Observability />}
          />
          <Route
            path="/security"
            element={<SecurityDashboard />}
          />
          <Route
            path="/documents"
            element={<DocumentsPage />}
          />
        </Route>
        <Route path="/gitrepo" element={<GitRepo />} />
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </Router>
  );
}

export default App;