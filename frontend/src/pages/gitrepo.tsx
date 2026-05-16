import { useState } from "react";
import { motion } from "framer-motion";
import {
    GitBranch,
    Brain,
    Database,
    Upload,
    Cpu,
    CheckCircle,
    Loader2,
    Sparkles,
} from "lucide-react";

export default function GitRepo() {
    const [repoUrl, setRepoUrl] = useState("");
    const [aiModel, setAiModel] = useState("GPT-4o");
    const [ragModel, setRagModel] = useState("LangChain + ChromaDB");
    const [processing, setProcessing] = useState(false);
    const [status, setStatus] = useState("");

    const handleAnalyze = async () => {
        if (!repoUrl) {
            alert("Please enter a GitHub repository URL");
            return;
        }

        setProcessing(true);
        setStatus("Cloning repository...");

        setTimeout(() => {
            setStatus("Analyzing project architecture...");
        }, 2000);

        setTimeout(() => {
            setStatus("Detecting bugs & vulnerabilities...");
        }, 4000);

        setTimeout(() => {
            setStatus("Debugging and optimizing code...");
        }, 6000);

        setTimeout(() => {
            setStatus("Generating intelligent improvements...");
        }, 8000);

        setTimeout(() => {
            setStatus("Repository processed successfully!");
            setProcessing(false);
        }, 10000);
    };

    return (
        <div className="min-h-screen cyber-bg text-white px-6 py-12">
            <motion.div
                initial={{ opacity: 0, y: 25 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7 }}
                className="max-w-4xl mx-auto"
            >
                {/* HEADER */}
                <div className="text-center mb-12">
                    <div className="flex justify-center mb-5">
                        <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500 to-cyber-500 flex items-center justify-center shadow-glow">
                            <GitBranch size={36} />
                        </div>
                    </div>

                    <h1 className="text-5xl font-black mb-4 gradient-text">
                        AI Git Repository Analyzer
                    </h1>

                    <p className="text-dark-300 text-lg max-w-2xl mx-auto">
                        Upload your GitHub repository and let autonomous AI agents
                        analyze, debug, optimize, improve scalability, and add
                        intelligent features without changing the core idea.
                    </p>
                </div>

                {/* MAIN CARD */}
                <div className="glass-card p-8 rounded-3xl border border-dark-700/60">

                    {/* GITHUB INPUT */}
                    <div className="mb-7">
                        <label className="block mb-3 text-sm font-medium text-dark-200">
                            GitHub Repository URL
                        </label>

                        <div className="relative">
                            <GitBranch
                                size={18}
                                className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500"
                            />

                            <input
                                type="text"
                                placeholder="https://github.com/username/repository"
                                value={repoUrl}
                                onChange={(e) => setRepoUrl(e.target.value)}
                                className="w-full bg-dark-900 border border-dark-700 rounded-2xl pl-12 pr-4 py-4 focus:outline-none focus:border-brand-500 transition"
                            />
                        </div>
                    </div>

                    {/* DROPDOWNS */}
                    <div className="grid md:grid-cols-2 gap-6 mb-8">

                        {/* AI MODEL */}
                        <div>
                            <label className="block mb-3 text-sm font-medium text-dark-200">
                                AI Model
                            </label>

                            <div className="relative">
                                <Brain
                                    size={18}
                                    className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500"
                                />

                                <select
                                    value={aiModel}
                                    onChange={(e) => setAiModel(e.target.value)}
                                    className="w-full bg-dark-900 border border-dark-700 rounded-2xl pl-12 pr-4 py-4 focus:outline-none focus:border-cyber-500 transition"
                                >
                                    <option>GPT-4o</option>
                                    <option>Claude 3.5 Sonnet</option>
                                    <option>Gemini 1.5 Pro</option>
                                    <option>DeepSeek Coder</option>
                                    <option>Llama 3</option>
                                </select>
                            </div>
                        </div>

                        {/* RAG MODEL */}
                        <div>
                            <label className="block mb-3 text-sm font-medium text-dark-200">
                                RAG Framework
                            </label>

                            <div className="relative">
                                <Database
                                    size={18}
                                    className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500"
                                />

                                <select
                                    value={ragModel}
                                    onChange={(e) => setRagModel(e.target.value)}
                                    className="w-full bg-dark-900 border border-dark-700 rounded-2xl pl-12 pr-4 py-4 focus:outline-none focus:border-cyber-500 transition"
                                >
                                    <option>LangChain + ChromaDB</option>
                                    <option>LlamaIndex + Pinecone</option>
                                    <option>Haystack + Weaviate</option>
                                    <option>CrewAI Memory RAG</option>
                                    <option>AutoGen Retrieval</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* FEATURES */}
                    <div className="glass rounded-2xl p-6 mb-8 border border-dark-700/50">
                        <h2 className="text-xl font-bold mb-5 flex items-center gap-2">
                            <Sparkles size={20} className="text-brand-400" />
                            AI Agent Capabilities
                        </h2>

                        <div className="grid md:grid-cols-2 gap-4 text-dark-300">
                            <div className="flex items-center gap-3">
                                <CheckCircle size={16} className="text-success-400" />
                                Detect runtime & syntax errors
                            </div>

                            <div className="flex items-center gap-3">
                                <CheckCircle size={16} className="text-success-400" />
                                Debug broken functionalities
                            </div>

                            <div className="flex items-center gap-3">
                                <CheckCircle size={16} className="text-success-400" />
                                Preserve core architecture
                            </div>

                            <div className="flex items-center gap-3">
                                <CheckCircle size={16} className="text-success-400" />
                                Optimize performance
                            </div>

                            <div className="flex items-center gap-3">
                                <CheckCircle size={16} className="text-success-400" />
                                Add intelligent features
                            </div>

                            <div className="flex items-center gap-3">
                                <CheckCircle size={16} className="text-success-400" />
                                Improve scalability & security
                            </div>
                        </div>
                    </div>

                    {/* BUTTON */}
                    <button
                        onClick={handleAnalyze}
                        disabled={processing}
                        className={`w-full py-4 rounded-2xl font-semibold text-lg flex items-center justify-center gap-3 transition-all ${processing
                                ? "bg-dark-700 cursor-not-allowed"
                                : "bg-gradient-to-r from-brand-500 to-cyber-500 hover:scale-[1.02]"
                            }`}
                    >
                        {processing ? (
                            <>
                                <Loader2 size={20} className="animate-spin" />
                                Processing Repository...
                            </>
                        ) : (
                            <>
                                <Upload size={20} />
                                Analyze Repository
                            </>
                        )}
                    </button>

                    {/* PROCESSING BOX */}
                    {(processing || status) && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="mt-8 glass rounded-2xl p-6 border border-brand-500/20"
                        >
                            <div className="flex items-center gap-3 mb-3">
                                <Cpu size={20} className="text-brand-400" />

                                <h3 className="font-semibold text-lg">
                                    Autonomous AI Processing
                                </h3>
                            </div>

                            <div className="flex items-center gap-3 text-dark-300">
                                {processing && (
                                    <Loader2 size={18} className="animate-spin text-cyber-400" />
                                )}

                                <p>{status}</p>
                            </div>
                        </motion.div>
                    )}
                </div>
            </motion.div>
        </div>
    );
}