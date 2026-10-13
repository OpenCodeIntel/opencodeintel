import { Link } from 'react-router-dom'
import { DocsLayout } from '@/components/docs'
import { 
  Zap, 
  Search, 
  GitBranch, 
  AlertTriangle, 
  Palette, 
  Terminal, 
  Server,
  ArrowRight,
  BookOpen,
  Code,
  ExternalLink
} from 'lucide-react'

interface QuickLinkProps {
  title: string
  description: string
  href: string
  icon: React.ReactNode
  time?: string
}

function QuickLink({ title, description, href, icon, time }: QuickLinkProps) {
  return (
    <Link 
      to={href}
      className="group relative flex flex-col p-5 bg-white/[0.02] border border-white/10 rounded-xl hover:border-blue-500/50 hover:bg-blue-500/5 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="p-2.5 bg-blue-500/10 rounded-lg text-blue-400 group-hover:bg-blue-500/20 transition-colors">
          {icon}
        </div>
        {time && (
          <span className="text-xs text-gray-500">{time}</span>
        )}
      </div>
      <h3 className="text-lg font-semibold text-white mb-1 group-hover:text-blue-400 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-gray-400 mb-3">{description}</p>
      <span className="inline-flex items-center gap-1 text-sm text-blue-400 mt-auto">
        Learn more
        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
      </span>
    </Link>
  )
}

interface FeatureCardProps {
  title: string
  description: string
  href: string
  icon: React.ReactNode
}

function FeatureCard({ title, description, href, icon }: FeatureCardProps) {
  return (
    <Link 
      to={href}
      className="group flex items-start gap-4 p-4 rounded-lg hover:bg-white/5 transition-colors"
    >
      <div className="p-2 bg-white/5 rounded-lg text-gray-400 group-hover:text-blue-400 group-hover:bg-blue-500/10 transition-colors">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-white group-hover:text-blue-400 transition-colors">
          {title}
        </h3>
        <p className="text-sm text-gray-400 mt-0.5">{description}</p>
      </div>
      <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 group-hover:translate-x-1 transition-all shrink-0 mt-1" />
    </Link>
  )
}

export function DocsHomePage() {
  return (
    <DocsLayout showToc={false}>
      <div className="max-w-4xl">
        {/* Hero */}
        <div className="mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 tracking-tight">
            OpenCodeIntel Docs
          </h1>
          <p className="text-xl text-gray-400 leading-relaxed max-w-2xl">
            Give your AI assistant deep understanding of your codebase. Semantic search, 
            dependency analysis, and impact prediction. Set up in 5 minutes.
          </p>
        </div>

        {/* Quick Start Cards */}
        <section className="mb-16">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Get Started
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <QuickLink
              title="Quick Start"
              description="Get up and running with OpenCodeIntel in under 5 minutes."
              href="/docs/quickstart"
              icon={<Zap className="w-5 h-5" />}
              time="5 min"
            />
            <QuickLink
              title="MCP Setup"
              description="Connect OpenCodeIntel to Claude Desktop for AI-powered code intelligence."
              href="/docs/mcp-setup"
              icon={<Terminal className="w-5 h-5" />}
              time="5 min"
            />
            <QuickLink
              title="Self-Hosting"
              description="Deploy your own instance with Docker or on your infrastructure."
              href="/docs/deployment/docker"
              icon={<Server className="w-5 h-5" />}
              time="15 min"
            />
          </div>
        </section>

        {/* Features */}
        <section className="mb-16">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Core Features
          </h2>
          <div className="bg-white/[0.02] border border-white/10 rounded-xl divide-y divide-white/5">
            <FeatureCard
              title="Semantic Search"
              description="Find code by meaning, not keywords. Search for 'error handling' and find processFailure()."
              href="/docs/features/search"
              icon={<Search className="w-5 h-5" />}
            />
            <FeatureCard
              title="Dependency Analysis"
              description="Visualize your architecture. See how files connect and identify critical components."
              href="/docs/features/dependencies"
              icon={<GitBranch className="w-5 h-5" />}
            />
            <FeatureCard
              title="Impact Prediction"
              description="Know what breaks before you change it. See the blast radius of any modification."
              href="/docs/features/impact"
              icon={<AlertTriangle className="w-5 h-5" />}
            />
            <FeatureCard
              title="Code Style Analysis"
              description="Understand team conventions. Write code that fits in with existing patterns."
              href="/docs/features/style"
              icon={<Palette className="w-5 h-5" />}
            />
          </div>
        </section>

        {/* Why OpenCodeIntel */}
        <section className="mb-16">
          <div className="p-6 sm:p-8 bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-transparent border border-white/10 rounded-xl">
            <h2 className="text-2xl font-semibold text-white mb-4">Why OpenCodeIntel?</h2>
            <div className="space-y-4 text-gray-300">
              <p>
                <strong className="text-white">The problem:</strong> AI coding assistants are powerful, 
                but they are flying blind. They cannot search your actual codebase, do not understand 
                your architecture, and have no clue what breaks when you change something.
              </p>
              <p>
                <strong className="text-white">The solution:</strong> OpenCodeIntel is a platform (web app, REST API and MCP server) that 
                gives AI assistants persistent memory of your codebase. Not just file contents but 
                semantic understanding, dependency graphs, and impact analysis.
              </p>
              <p>
                <strong className="text-white">The result:</strong> Claude that actually knows your code. 
                Ask "where is the auth middleware?" and get real answers, not guesses.
              </p>
            </div>
          </div>
        </section>

        {/* API Reference */}
        <section className="mb-16">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            API Reference
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <Link
              to="/docs/api"
              className="group flex items-center gap-4 p-4 bg-white/[0.02] border border-white/10 rounded-xl hover:border-blue-500/30 hover:bg-white/[0.04] transition-all"
            >
              <div className="p-2.5 bg-white/5 rounded-lg">
                <Code className="w-5 h-5 text-gray-400 group-hover:text-blue-400 transition-colors" />
              </div>
              <div>
                <h3 className="font-medium text-white group-hover:text-blue-400 transition-colors">REST API</h3>
                <p className="text-sm text-gray-500">Full API reference with examples</p>
              </div>
            </Link>
            <Link
              to="/docs/mcp-tools"
              className="group flex items-center gap-4 p-4 bg-white/[0.02] border border-white/10 rounded-xl hover:border-blue-500/30 hover:bg-white/[0.04] transition-all"
            >
              <div className="p-2.5 bg-white/5 rounded-lg">
                <Terminal className="w-5 h-5 text-gray-400 group-hover:text-blue-400 transition-colors" />
              </div>
              <div>
                <h3 className="font-medium text-white group-hover:text-blue-400 transition-colors">MCP Tools</h3>
                <p className="text-sm text-gray-500">Tools available to AI assistants</p>
              </div>
            </Link>
          </div>
        </section>

        {/* Resources */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Resources
          </h2>
          <div className="flex flex-wrap gap-3">
            <a 
              href="https://github.com/OpenCodeIntel/opencodeintel" 
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
              GitHub
            </a>
            <a 
              href="https://github.com/OpenCodeIntel/opencodeintel/issues" 
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              <AlertTriangle className="w-4 h-4" />
              Report Issue
            </a>
            <a 
              href="https://opencodeintel.com" 
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="w-4 h-4" />
              Try Hosted Version
            </a>
          </div>
        </section>
      </div>
    </DocsLayout>
  )
}
