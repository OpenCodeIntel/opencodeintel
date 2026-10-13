import { 
  DocsLayout,
  DocsCodeBlock,
  DocsCodeTabs,
  DocsCallout,
  DocsPrerequisites,
  DocsLearningObjectives,
  DocsPagination,
  TimeEstimate,
  Step,
  StepList,
  TOCItem
} from '@/components/docs'
import { Terminal } from 'lucide-react'

const tocItems: TOCItem[] = [
  { id: 'what-is-mcp', title: 'What is MCP?', level: 2 },
  { id: 'prerequisites', title: 'Prerequisites', level: 2 },
  { id: 'setup-steps', title: 'Setup Steps', level: 2 },
  { id: 'available-tools', title: 'Available Tools', level: 2 },
  { id: 'example-prompts', title: 'Example Prompts', level: 2 },
  { id: 'troubleshooting', title: 'Troubleshooting', level: 2 },
]

export function MCPSetupPage() {
  return (
    <DocsLayout toc={tocItems}>
      {/* Header */}
      <div className="mb-8 pb-8 border-b border-white/10">
        <div className="flex items-center gap-3 mb-4">
          <TimeEstimate minutes={5} />
        </div>
        <h1 className="text-4xl font-bold text-white mb-4">MCP Setup Guide</h1>
        <p className="text-xl text-gray-400">
          Connect OpenCodeIntel to Claude Desktop in under 5 minutes. Give your AI assistant 
          persistent memory of your entire codebase.
        </p>
      </div>

      <DocsLearningObjectives items={[
        { text: 'Understand what MCP is and why it matters' },
        { text: 'Configure Claude Desktop to use OpenCodeIntel' },
        { text: 'Use semantic search, dependency analysis, and impact prediction' },
      ]} />

      {/* Intro */}
      <p className="text-gray-300 text-lg leading-relaxed mb-6">
        Most AI coding assistants forget your codebase the moment you close the chat. 
        You explain your auth flow, close the window, come back tomorrow, and Claude 
        has no idea what you were talking about.
      </p>
      <p className="text-gray-300 text-lg leading-relaxed mb-8">
        OpenCodeIntel fixes this. Its MCP server gives Claude (or any MCP-compatible AI) 
        persistent access to your codebase: semantic search, dependency graphs, impact analysis, 
        the works.
      </p>

      {/* What is MCP */}
      <h2 id="what-is-mcp" className="text-2xl font-semibold text-white mt-12 mb-4">What is MCP?</h2>
      <p className="text-gray-300 leading-relaxed mb-4">
        MCP (Model Context Protocol) is Anthropic's open standard for connecting AI assistants 
        to external tools and data sources. Think of it as USB for AI: a universal way to 
        plug in capabilities.
      </p>
      <p className="text-gray-300 leading-relaxed mb-4">
        Instead of copy-pasting code into Claude, MCP lets Claude directly search your codebase, 
        analyze dependencies, and understand impact of changes. 
        <strong className="text-white"> The result?</strong> Claude that actually knows your code.
      </p>

      {/* Prerequisites */}
      <h2 id="prerequisites" className="text-2xl font-semibold text-white mt-12 mb-4">Prerequisites</h2>
      <DocsPrerequisites 
        defaultOpen={true}
        items={[
          { text: 'Claude Desktop installed', href: 'https://claude.ai/download' },
          { text: 'OpenCodeIntel backend running (locally or hosted)' },
          { text: 'Python 3.11+ for the MCP server' },
          { text: '5 minutes of your time' },
        ]} 
      />

      {/* Setup Steps */}
      <h2 id="setup-steps" className="text-2xl font-semibold text-white mt-12 mb-6">Setup Steps</h2>
      
      <StepList>
        <Step number={1} title="Clone the MCP Server">
          <p>If you have not already, grab the OpenCodeIntel repo:</p>
          <DocsCodeBlock language="bash">
{`git clone https://github.com/OpenCodeIntel/opencodeintel.git
cd opencodeintel/mcp-server`}
          </DocsCodeBlock>
        </Step>

        <Step number={2} title="Install Dependencies">
          <p>Install the required Python packages:</p>
          <DocsCodeBlock language="bash">
{`pip install -r requirements.txt`}
          </DocsCodeBlock>
          <DocsCallout type="tip">
            No virtual environment drama needed for a simple MCP server. Just install and go.
          </DocsCallout>
        </Step>

        <Step number={3} title="Configure Environment">
          <p>Create your <code className="px-1.5 py-0.5 bg-white/10 rounded text-sm">.env</code> file:</p>
          <DocsCodeBlock language="bash">
{`cp .env.example .env`}
          </DocsCodeBlock>
          <p>Edit <code className="px-1.5 py-0.5 bg-white/10 rounded text-sm">.env</code> with your settings:</p>
          <DocsCodeBlock language="bash" filename=".env">
{`# Where is your CodeIntel backend running?
BACKEND_API_URL=http://localhost:8000

# Your API key (get this from the CodeIntel dashboard)
API_KEY=your-api-key-here`}
          </DocsCodeBlock>
          <DocsCallout type="info">
            Using hosted OpenCodeIntel? Replace <code>localhost:8000</code> with your hosted URL.
          </DocsCallout>
        </Step>

        <Step number={4} title="Configure Claude Desktop">
          <p>This is where the magic happens. You need to tell Claude Desktop about the MCP server.</p>
          <p className="mb-4"><strong className="text-white">Find your config file:</strong></p>
          
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-2 text-gray-400 font-medium">OS</th>
                  <th className="text-left py-2 text-gray-400 font-medium">Config Location</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                <tr className="border-b border-white/5">
                  <td className="py-2">macOS</td>
                  <td className="py-2 font-mono text-xs">~/Library/Application Support/Claude/claude_desktop_config.json</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2">Windows</td>
                  <td className="py-2 font-mono text-xs">%APPDATA%\Claude\claude_desktop_config.json</td>
                </tr>
                <tr>
                  <td className="py-2">Linux</td>
                  <td className="py-2 font-mono text-xs">~/.config/Claude/claude_desktop_config.json</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="mb-4"><strong className="text-white">Add OpenCodeIntel to your config:</strong></p>
          <DocsCodeBlock language="json" filename="claude_desktop_config.json">
{`{
  "mcpServers": {
    "codeintel": {
      "command": "python",
      "args": ["/absolute/path/to/opencodeintel/mcp-server/server.py"],
      "env": {
        "BACKEND_API_URL": "http://localhost:8000",
        "API_KEY": "your-api-key-here"
      }
    }
  }
}`}
          </DocsCodeBlock>
          
          <DocsCallout type="warning" title="Important">
            Use the absolute path to <code>server.py</code>. Relative paths will not work.
          </DocsCallout>
        </Step>

        <Step number={5} title="Restart Claude Desktop">
          <p>
            Completely quit Claude Desktop (not just close the window) and reopen it.
          </p>
          <p>
            You should see a 🔧 icon in the chat input. That means MCP tools are available.
          </p>
          <DocsCallout type="success" title="You are all set!">
            Claude now has access to your codebase through OpenCodeIntel.
          </DocsCallout>
        </Step>
      </StepList>

      {/* Available Tools */}
      <h2 id="available-tools" className="text-2xl font-semibold text-white mt-12 mb-4">Available Tools</h2>
      <p className="text-gray-300 mb-6">Once connected, Claude has access to these tools:</p>
      
      <div className="space-y-6">
        <ToolCard
          name="search_code"
          description="Semantic search across your codebase. Finds code by meaning, not just keywords."
          examples={[
            'Find authentication middleware',
            'Show me error handling patterns',
            'Where is the database connection logic?',
          ]}
        />
        <ToolCard
          name="list_repositories"
          description="See all indexed repositories."
          examples={[
            'What repos do you have access to?',
            'List my codebases',
          ]}
        />
        <ToolCard
          name="get_dependency_graph"
          description="Understand how files connect. See which files are critical vs isolated."
          examples={[
            'Show me the dependency graph for this repo',
            'What files does auth.py depend on?',
          ]}
        />
        <ToolCard
          name="analyze_code_style"
          description="Team patterns: naming conventions, async usage, type hints, common imports."
          examples={[
            'What coding conventions does this repo use?',
            'Is this team using snake_case or camelCase?',
          ]}
        />
        <ToolCard
          name="analyze_impact"
          description="Before you change a file, know what breaks. Shows direct dependents, indirect impact, and related tests."
          examples={[
            'What happens if I modify src/auth/middleware.py?',
            'What is the blast radius of changing this file?',
          ]}
        />
        <ToolCard
          name="get_repository_insights"
          description="High-level overview: file count, critical files, architecture patterns."
          examples={[
            'Give me an overview of this codebase',
            'What are the most important files here?',
          ]}
        />
      </div>

      {/* Example Prompts */}
      <h2 id="example-prompts" className="text-2xl font-semibold text-white mt-12 mb-4">Example Prompts</h2>
      <p className="text-gray-300 mb-6">Here is how to actually use OpenCodeIntel with Claude:</p>
      
      <div className="space-y-4">
        <PromptExample
          title="Understanding new code"
          prompt="I just joined this project. Search for the main entry points and explain the architecture."
        />
        <PromptExample
          title="Before refactoring"
          prompt="I want to refactor UserService. What is the impact? What tests cover it?"
        />
        <PromptExample
          title="Finding patterns"
          prompt="How does this codebase handle errors? Find examples of error handling."
        />
        <PromptExample
          title="Code review prep"
          prompt="Search for all usages of the deprecated oldAuth() function."
        />
        <PromptExample
          title="Matching team style"
          prompt="Analyze the code style. I want to write a new module that fits in."
        />
      </div>

      {/* Troubleshooting */}
      <h2 id="troubleshooting" className="text-2xl font-semibold text-white mt-12 mb-4">Troubleshooting</h2>
      
      <div className="space-y-6">
        <TroubleshootItem
          problem="Claude does not show the 🔧 icon"
          solutions={[
            'Check the config path. Make sure you are editing the right config file.',
            'Validate JSON. A single missing comma breaks everything.',
            'Use absolute paths. Relative paths do not work.',
            'Restart fully. Quit Claude Desktop completely, not just close window.',
          ]}
        />
        <TroubleshootItem
          problem="Connection refused errors"
          solutions={[
            'Your CodeIntel backend is not running. Start it with: cd opencodeintel/backend && python main.py',
          ]}
        />
        <TroubleshootItem
          problem="Unauthorized errors"
          solutions={[
            'Check your API_KEY in both the .env file in mcp-server/ and the Claude Desktop config.',
            'They need to match what your backend expects.',
          ]}
        />
        <TroubleshootItem
          problem="Tools work but return no results"
          solutions={[
            'You probably have not indexed any repositories yet.',
            'Open the CodeIntel dashboard and add a repo first.',
          ]}
        />
        <TroubleshootItem
          problem="Python command not found"
          solutions={[
            'On macOS, you might need python3 instead of python.',
            'Update your Claude Desktop config to use "command": "python3"',
          ]}
        />
      </div>

      {/* Pagination */}
      <DocsPagination
        prev={{ title: 'Quick Start', href: '/docs/quickstart' }}
        next={{ title: 'MCP Tools Reference', href: '/docs/mcp-tools' }}
      />
    </DocsLayout>
  )
}

// Helper components
function ToolCard({ name, description, examples }: { name: string; description: string; examples: string[] }) {
  return (
    <div className="p-4 bg-white/[0.02] border border-white/10 rounded-lg">
      <h3 className="font-mono text-blue-400 font-medium mb-2">{name}</h3>
      <p className="text-gray-300 text-sm mb-3">{description}</p>
      <div className="space-y-1">
        {examples.map((example, i) => (
          <p key={i} className="text-sm text-gray-500 italic">"{example}"</p>
        ))}
      </div>
    </div>
  )
}

function PromptExample({ title, prompt }: { title: string; prompt: string }) {
  return (
    <div className="p-4 bg-white/[0.02] border border-white/10 rounded-lg">
      <p className="text-sm text-gray-400 mb-1">{title}:</p>
      <p className="text-white">"{prompt}"</p>
    </div>
  )
}

function TroubleshootItem({ problem, solutions }: { problem: string; solutions: string[] }) {
  return (
    <div>
      <h3 className="font-medium text-white mb-2">{problem}</h3>
      <ul className="space-y-1">
        {solutions.map((solution, i) => (
          <li key={i} className="text-gray-400 text-sm flex items-start gap-2">
            <span className="text-gray-600 mt-1">•</span>
            {solution}
          </li>
        ))}
      </ul>
    </div>
  )
}
