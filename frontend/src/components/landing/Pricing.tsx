import { motion } from 'framer-motion'
import { Check, Sparkles } from 'lucide-react'

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'For open source and hobby projects',
    features: ['Up to 3 repositories', 'Semantic code search', 'Dependency visualization', 'Community support', 'Public repos only'],
    cta: 'Get Started',
    ctaHref: '/signup',
    popular: false,
  },
  {
    name: 'Pro',
    price: '$19',
    period: '/month',
    description: 'For professional developers',
    features: ['Unlimited repositories', 'Private repo support', 'API access', 'MCP server integration', 'Priority indexing', 'Email support'],
    cta: 'Join Waitlist',
    ctaHref: '/waitlist',
    popular: true,
    badge: 'Coming Soon',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For teams that need control',
    features: ['Self-hosted deployment', 'SSO / SAML authentication', 'Dedicated support', 'Custom integrations', 'SLA guarantee', 'On-premise option'],
    cta: 'Contact Sales',
    ctaHref: 'mailto:devanshurajesh@gmail.com?subject=CodeIntel%20Enterprise',
    popular: false,
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.12, delayChildren: 0.1 } }
}

const cardVariants = {
  hidden: { opacity: 0, y: 40, scale: 0.95 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { type: 'spring', stiffness: 200, damping: 20 } }
}

/**
 * Render the pricing section with three animated plan cards, per-feature lists, optional badges, and CTAs.
 *
 * The component includes a centered header, a responsive grid of plan cards (one highlighted as popular), animated entrance and hover interactions via Framer Motion, and a footer note about updates and security patches.
 *
 * @returns The JSX element for the complete pricing section containing plan cards, feature lists, badges, and call-to-action buttons.
 */
export function Pricing() {
  return (
    <section id="pricing" className="py-20 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <motion.div
          className="text-center mb-14"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.25, 0.4, 0.25, 1] }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">Simple, transparent pricing</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Start free, upgrade when you need more. No hidden fees.</p>
        </motion.div>

        <motion.div
          className="grid md:grid-cols-3 gap-6 lg:gap-8"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
        >
          {PLANS.map((plan) => (
            <motion.div
              key={plan.name}
              variants={cardVariants}
              whileHover={{ 
                y: plan.popular ? -12 : -8, 
                transition: { type: 'spring', stiffness: 400, damping: 25 } 
              }}
              className={`relative p-6 lg:p-8 rounded-2xl border transition-all duration-300 ${
                plan.popular
                  ? 'border-accent bg-accent/5 shadow-2xl shadow-accent/10 z-10'
                  : 'border-border/50 bg-card/30 hover:bg-card/50 hover:border-border'
              }`}
            >
              {plan.badge && (
                <motion.div 
                  className="absolute -top-3 left-1/2 -translate-x-1/2"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent text-white text-xs font-medium shadow-lg shadow-accent/30">
                    <Sparkles className="w-3 h-3" />
                    {plan.badge}
                  </div>
                </motion.div>
              )}

              <div className="mb-6">
                <h3 className="text-xl font-semibold text-foreground mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                  {plan.period && <span className="text-muted-foreground">{plan.period}</span>}
                </div>
                <p className="text-sm text-muted-foreground mt-2">{plan.description}</p>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, i) => (
                  <motion.li 
                    key={feature} 
                    className="flex items-start gap-3 text-sm"
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.1 * i }}
                  >
                    <Check className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{feature}</span>
                  </motion.li>
                ))}
              </ul>

              <motion.a
                href={plan.ctaHref}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`block w-full py-3 px-4 rounded-lg text-center text-sm font-medium transition-all ${
                  plan.popular
                    ? 'bg-accent text-white hover:bg-accent/90 shadow-lg shadow-accent/20'
                    : 'border border-border text-foreground hover:bg-muted/50'
                }`}
              >
                {plan.cta}
              </motion.a>
            </motion.div>
          ))}
        </motion.div>

        <motion.p
          className="text-center text-sm text-muted-foreground/60 mt-8"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
        >
          All plans include automatic updates and security patches
        </motion.p>
      </div>
    </section>
  )
}