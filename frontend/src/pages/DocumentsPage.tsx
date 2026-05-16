import { motion } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';
import { FileText, Upload, Trash2, ChevronDown, Code, AlertTriangle } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { api } from '../services/api';

interface Document {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  created_at: number;
  chunks: number;
}

export function DocumentsPage() {
  const { token } = useAppStore();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [chunks, setChunks] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const docs = await api.get('/documents', token);
      setDocuments(docs);
    } catch (e) {}
  };

  const handleUpload = async (file: File) => {
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadFile('/documents/upload', file, token);
      await fetchDocuments();
    } catch (e) {
      console.error('Upload failed:', e);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await api.delete(`/documents/${docId}`, token);
      await fetchDocuments();
      if (selectedDoc === docId) setSelectedDoc(null);
    } catch (e) {}
  };

  const viewChunks = async (docId: string) => {
    if (selectedDoc === docId) {
      setSelectedDoc(null);
      return;
    }
    try {
      const data = await api.get(`/documents/${docId}/chunks`, token);
      setSelectedDoc(docId);
      setChunks(data.sample_chunks || []);
    } catch (e) {}
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const ALLOWED = ['pdf', 'docx', 'txt', 'md', 'py', 'js', 'ts', 'json', 'yaml'];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Document Intelligence</h1>
        <p className="text-dark-400 text-sm mt-1">Lightweight RAG — Upload context for agent reasoning</p>
      </div>

      {/* Upload zone */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`glass-card p-8 text-center border-2 border-dashed transition-all cursor-pointer ${
          dragOver ? 'border-brand-500/60 bg-brand-500/5' : 'border-dark-700/60 hover:border-brand-500/30'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept={ALLOWED.map(e => `.${e}`).join(',')}
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />
        <div className="w-12 h-12 rounded-2xl bg-brand-500/15 flex items-center justify-center mx-auto mb-4">
          <Upload size={22} className="text-brand-400" />
        </div>
        {uploading ? (
          <div>
            <p className="text-brand-300 font-medium mb-1">Processing document...</p>
            <div className="w-32 mx-auto mt-3 progress-track">
              <div className="progress-fill w-3/4" />
            </div>
          </div>
        ) : (
          <div>
            <p className="text-dark-200 font-medium mb-1">Drop a file or click to upload</p>
            <p className="text-dark-500 text-sm">
              Supported: {ALLOWED.join(', ')} · Max 50MB
            </p>
          </div>
        )}
      </motion.div>

      {/* RAG info */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-3 p-4 rounded-xl bg-cyber-500/5 border border-cyber-500/20"
      >
        <Code size={16} className="text-cyber-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-cyber-300 font-medium mb-1">Lightweight RAG Pipeline</p>
          <p className="text-xs text-dark-400">
            Uploaded documents are parsed, chunked (500 chars with 50-char overlap),
            and made available for agent context retrieval. Agents use document chunks
            during reasoning to provide domain-specific outputs.
          </p>
        </div>
      </motion.div>

      {/* Documents list */}
      {documents.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="w-14 h-14 rounded-2xl bg-dark-800 flex items-center justify-center mx-auto mb-4">
            <FileText size={22} className="text-dark-600" />
          </div>
          <p className="text-dark-300 font-medium">No documents uploaded</p>
          <p className="text-dark-500 text-sm mt-1">Upload PDFs, docs, or code files for RAG context</p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc, i) => (
            <motion.div
              key={doc.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass-card p-4"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center flex-shrink-0">
                  <FileText size={16} className="text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-dark-200 text-sm truncate">{doc.filename}</div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="badge badge-completed">{doc.file_type.toUpperCase()}</span>
                    <span className="text-xs text-dark-500">{(doc.size_bytes / 1024).toFixed(1)} KB</span>
                    <span className="text-xs text-dark-500">{doc.chunks} chunks</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => viewChunks(doc.id)}
                    className="btn-secondary text-xs px-3 py-1.5"
                  >
                    <ChevronDown size={12} className={selectedDoc === doc.id ? 'rotate-180 transition-transform' : 'transition-transform'} />
                    Chunks
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="btn-danger px-3 py-1.5 text-xs"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>

              {selectedDoc === doc.id && chunks.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-4 pt-4 border-t border-dark-800"
                >
                  <div className="text-xs text-dark-500 mb-2">Sample Chunks (first {chunks.length})</div>
                  <div className="space-y-2">
                    {chunks.slice(0, 3).map((chunk, ci) => (
                      <div key={ci} className="p-3 rounded-lg bg-dark-900/60 border border-dark-800 text-xs font-mono text-dark-300 line-clamp-3">
                        <span className="text-dark-600">[chunk {ci + 1}] </span>
                        {chunk}
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
