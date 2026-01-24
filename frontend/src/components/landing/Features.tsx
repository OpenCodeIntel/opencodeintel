import { motion } from 'framer-motion'
import { Search, Zap, GitBranch, Brain, Lock, Terminal } from 'lucide-react'

const FEATURES = [
  {
    icon: Search,
    title: 'Semantic Search',
    description: 'Find code by what it does, not what it\'s named. Ask "retry logic with exponential backoff" and get exactly that.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    glow: 'group-hover:shadow-blue-500/20',
  },
  {
    icon: Brain,
    title: 'Understands Context',
    description: 'Knows the difference between a Flask route handler and a FastAPI dependency. Context-aware results every time.',
    color: 'text-violet-400',
    bg: 'bg-violet-500/10',
    glow: 'group-hover:shadow-violet-500/20',
  },
  {
    icon: Zap,
    title: 'Instant Results',
    description: 'Sub-100ms search across your entire codebase. No waiting, no spinning, just answers.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    glow: 'group-hover:shadow-amber-500/20',
  },
  {
    icon: GitBranch,
    title: 'Dependency Graph',
    description: 'See how code connects. Trace imports, find usages, understand impact before you change anything.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    glow: 'group-hover:shadow-emerald-500/20',
  },
  {
    icon: Terminal,
    title: 'MCP Integration',
    description: 'Works with Claude, Cursor, and any MCP-compatible AI. Your AI assistant finally understands your code.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    glow: 'group-hover:shadow-cyan-500/20',
  },
  {
    icon: Lock,
    title: 'Self-Host Option',
    description: 'Keep your code private. Run CodeIntel on your own infrastructure with full control.',
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
    glow: 'group-hover:shadow-rose-500/20',
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  visible: { 
    opacity: 1, 
    y: 0, 
    scale: 1,
    transition: { type: 'spring', stiffness: 200, damping: 20 }
  }
}

/**
 * Renders the "Features" section with an animated, responsive grid of feature cards.
 *
 * Each card displays an icon, title, and description and includes hover interactions and reveal animations.
 *
 * @returns A section element containing the animated, responsive grid of feature cards.
 */
export function Features() {
  return (
    <section id="features" className="py-20 px-6 relative">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-accent/[0.02] to-transparent pointer-events-none" />
      
      <div className="max-w-6xl mx-auto relative">
        {/* Section header */}
        <motion.div
          className="text-center mb-14"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.25, 0.4, 0.25, 1] }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Built for how developers actually work
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Not another code search tool. CodeIntel understands your codebase the way you do.
          </p>
        </motion.div>

        {/* Features grid */}
        <motion.div
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-5"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
        >
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              whileHover={{ 
                y: -8, 
                transition: { type: 'spring', stiffness: 400, damping: 25 } 
              }}
              className={`group relative p-6 rounded-xl border border-border/50 bg-card/30 
                hover:bg-card/50 hover:border-border transition-colors duration-300
                hover:shadow-xl ${feature.glow}`}
            >
              {/* Icon */}
              <motion.div 
                className={`w-11 h-11 rounded-xl ${feature.bg} flex items-center justify-center mb-4`}
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ type: 'spring', stiffness: 400, damping: 15 }}
              >
                <feature.icon className={`w-5 h-5 ${feature.color}`} />
              </motion.div>

              <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-accent transition-colors">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>

              {/* Subtle corner accent on hover */}
              <div className="absolute top-0 right-0 w-20 h-20 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                <div className={`absolute top-3 right-3 w-1.5 h-1.5 rounded-full ${feature.bg}`} />
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}