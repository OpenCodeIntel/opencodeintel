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

OpenCodeIntel searches by meaning, not just by name. Each function is embedded together with its name, signature and docstring, so you can search "retry logic with exponential backoff" and find it, even if those words appear nowhere in the file.`,
  },
  {
    q: 'What languages do you support?',
    a: `Python and JavaScript are indexed today. TypeScript files go through the JavaScript parser for now, so code that leans on type syntax can be missed. For Python, the style analysis also picks up Flask, FastAPI and Django patterns like routes, middleware and decorators.

A real TypeScript parser is the next language step, then Go and Rust. OpenCodeIntel is open source, so if you need a language we don't support yet, you can contribute a parser.`,
  },
  {
    q: 'How does MCP integration work?',
    a: `MCP (Model Context Protocol) is how AI assistants like Claude and Cursor talk to external tools. Alongside its web app and REST API, OpenCodeIntel ships a 12-tool MCP server that these tools can connect to.

Once connected, your AI assistant gains the ability to semantically search your entire codebase. When you ask Claude "how does authentication work in this project?", it can actually find and read the relevant code instead of guessing. It's like giving your AI assistant a senior developer's knowledge of your codebase.`,
  },
  {
    q: 'Is my code stored on your servers?',
    a: `Yes. To index a repository we clone it to our server and keep the clone, so later re-indexes only process the files that changed. Code is sent to OpenAI to create embeddings. The search index stores each function's embedding with its file path, signature, docstring and the first 1,000 characters of its code, so results can show you the match.

Deleting a repository from your dashboard removes the clone and its database records. Removing its entries from the search index is not automated yet; we're fixing that (issue #336).

If your code can't sit on our servers, you can self-host OpenCodeIntel. It's open source under the MIT license. Self-hosted, the clone stays on your machines, but embeddings are still created through the OpenAI API and the index lives in your own Pinecone account.`,
  },
  {
    q: 'How fast is indexing?',
    a: `Initial indexing time depends on the size of the repository. We parse your code, create embeddings and write the search index in parallel batches.

After the first index, updates are incremental: only the files changed since the last indexed commit are processed. On the public playground, a cold search takes 641ms at the median, and cached repeats come back in about 242ms.`,
  },
]

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
