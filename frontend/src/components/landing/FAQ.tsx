import { motion } from 'framer-motion'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

const FAQS = [
  {
    q: 'How is this different from GitHub search or grep?',
    a: `Think about the last time you joined a new codebase. You knew what you needed ("the function that retries API calls") but had no idea what it was called. GitHub search and grep need exact keywords. If the function is named make_request_with_backoff, you'd never find it by searching "retry logic."

CodeIntel actually understands what code does, not just what it's named. We use AI embeddings trained specifically on code semantics. So you can search "retry logic with exponential backoff" and find it, even if those words appear nowhere in the file.`,
  },
  {
    q: 'What languages do you support?',
    a: `Right now, Python is our focus. We have deep support for Flask, FastAPI, and Django, meaning we understand routes, middleware, decorators, and framework-specific patterns.

TypeScript and JavaScript are next on our roadmap, followed by Go and Rust. The good news: CodeIntel is completely open source. If you need a language we don't support yet, you can contribute a parser or sponsor its development. Our architecture is built to be language-agnostic from day one.`,
  },
  {
    q: 'How does MCP integration work?',
    a: `MCP (Model Context Protocol) is how AI assistants like Claude and Cursor talk to external tools. CodeIntel runs as an MCP server that these tools can connect to.

Once connected, your AI assistant gains the ability to semantically search your entire codebase. When you ask Claude "how does authentication work in this project?", it can actually find and read the relevant code instead of guessing. It's like giving your AI assistant a senior developer's knowledge of your codebase.`,
  },
  {
    q: 'Is my code stored on your servers?',
    a: `We never store your raw source code. What we store are vector embeddings, which are mathematical representations of what your code does. Think of it like storing a summary, not the actual document. You can delete these anytime from your dashboard.

But if you want complete control, you can self-host CodeIntel on your own infrastructure. It's fully open source under MIT license. Your code never leaves your servers, and you get the same search quality. Many teams with sensitive codebases go this route.`,
  },
  {
    q: 'How fast is indexing?',
    a: `For most repositories under 100,000 lines of code, initial indexing takes about 1-2 minutes. We parse your code, generate embeddings, and build the search index in parallel.

After the first index, updates are incremental. Change a file, and only that file gets re-indexed. This usually takes seconds. Search itself returns results in under 100ms regardless of how large your codebase is, because we're searching vectors, not scanning text.`,
  },
]

/**
 * Renders the FAQ section with an animated header, an accordion of frequently asked questions, and a contact link.
 *
 * @returns The section element containing the FAQ accordion and contact paragraph
 */
export function FAQ() {
  return (
    <section id="faq" className="py-24 px-6 relative">
      <div className="max-w-3xl mx-auto">
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Questions? Answers.
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Accordion type="single" collapsible className="space-y-3">
            {FAQS.map((faq, i) => (
              <AccordionItem
                key={i}
                value={`faq-${i}`}
                className="border border-border/50 rounded-xl px-6 bg-card/20"
              >
                <AccordionTrigger className="text-left text-foreground hover:no-underline py-5 text-[15px]">
                  {faq.q}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground pb-5 leading-relaxed text-sm">
                  {faq.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>

        <motion.p
          className="text-center text-sm text-muted-foreground mt-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
        >
          More questions?{' '}
          <a href="mailto:devanshurajesh@gmail.com" className="text-accent hover:underline">
            Get in touch
          </a>
        </motion.p>
      </div>
    </section>
  )
}