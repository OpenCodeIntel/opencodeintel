import { useState } from 'react'
import { Key, Plus, Copy, Check, Trash2, Clock, Shield, Terminal, AlertTriangle } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { API_URL } from '@/config/api'
import { cn } from '@/lib/utils'

interface APIKey {
  id: string
  name: string
  tier: string
  active: boolean
  created_at: string
  last_used_at: string | null
  key_preview: string
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'Never'
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 2592000) return `${Math.floor(seconds / 86400)}d ago`
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

async function fetchKeys(token: string): Promise<APIKey[]> {
  const res = await fetch(`${API_URL}/keys`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to load keys')
  const data = await res.json()
  return data.keys || []
}


// -- Small sub-components --

function TierBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    enterprise: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    pro: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    free: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  }
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border tracking-wide uppercase',
      styles[tier] ?? styles.free
    )}>
      {tier}
    </span>
  )
}

function CopyButton({ value, className }: { value: string; className?: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable -- silently ignore, user can select manually
    }
  }
  return (
    <button
      onClick={handleCopy}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-all shrink-0',
        copied
          ? 'bg-emerald-500/10 text-emerald-400'
          : 'bg-muted text-muted-foreground hover:text-foreground',
        className
      )}
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function APIKeysSkeleton() {
  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="w-10 h-10 rounded-xl" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-3.5 w-52" />
          </div>
        </div>
        <Skeleton className="h-9 w-32 rounded-md" />
      </div>
      <Skeleton className="h-px w-full" />
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="h-9 bg-muted/50 border-b border-border" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-6 px-4 py-4 border-b border-border last:border-0">
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-4 w-44" />
            <Skeleton className="h-5 w-14 rounded" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-14" />
          </div>
        ))}
      </div>
    </div>
  )
}


function EmptyState({ onGenerate }: { onGenerate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-2xl bg-muted border border-border flex items-center justify-center mb-4">
        <Key className="w-5 h-5 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-medium text-foreground mb-1">No API keys yet</h3>
      <p className="text-sm text-muted-foreground max-w-xs mb-6">
        Generate a key to authenticate API requests or connect your MCP server to Claude Desktop, Cursor, or any MCP client.
      </p>
      <Button onClick={onGenerate} size="sm" className="gap-2 h-8 text-xs px-3">
        <Plus className="w-3.5 h-3.5" />
        Generate API Key
      </Button>
    </div>
  )
}

// Key row -- table-style, hover reveals revoke button
function KeyRow({ apiKey, onRevoke, revoking }: { apiKey: APIKey; onRevoke: () => void; revoking: boolean }) {
  const isRevoked = !apiKey.active
  return (
    <div className={cn(
      'group grid items-center gap-4 px-4 py-3.5 border-b border-border last:border-0 transition-colors',
      'grid-cols-[1fr_200px_80px_110px_120px]',
      isRevoked ? 'opacity-50' : 'hover:bg-muted/20',
    )}>
      {/* Name + created date */}
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{apiKey.name}</p>
        <p className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Created {timeAgo(apiKey.created_at)}
        </p>
      </div>

      {/* Key preview + inline copy */}
      <div className="flex items-center gap-2 min-w-0">
        <code className="text-xs font-mono text-muted-foreground truncate flex-1">
          {apiKey.key_preview}
        </code>
        {!isRevoked && <CopyButton value={apiKey.key_preview} />}
      </div>

      {/* Tier */}
      <div><TierBadge tier={apiKey.tier} /></div>

      {/* Last used */}
      <span className="text-xs text-muted-foreground">
        {apiKey.last_used_at
          ? timeAgo(apiKey.last_used_at)
          : <span className="text-muted-foreground/40">Never</span>
        }
      </span>

      {/* Status dot + hover-reveal revoke */}
      <div className="flex items-center justify-end gap-3">
        <span className="inline-flex items-center gap-1.5">
          <span className={cn('w-1.5 h-1.5 rounded-full', apiKey.active ? 'bg-emerald-400' : 'bg-zinc-600')} />
          <span className={cn('text-xs font-medium', apiKey.active ? 'text-emerald-400' : 'text-muted-foreground')}>
            {apiKey.active ? 'Active' : 'Revoked'}
          </span>
        </span>
        {!isRevoked && (
          <button
            onClick={onRevoke}
            disabled={revoking}
            className={cn(
              'opacity-0 group-hover:opacity-100 p-1 rounded transition-all',
              'text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10',
            )}
            title="Revoke key"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}


// New key one-time reveal modal
function NewKeyRevealModal({ apiKey, onClose }: { apiKey: string | null; onClose: () => void }) {
  if (!apiKey) return null
  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <div className="w-6 h-6 rounded-md bg-emerald-500/10 flex items-center justify-center">
              <Key className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            API key generated
          </DialogTitle>
          <DialogDescription>Copy this now. It will not be shown again.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* Key display with copy footer */}
          <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
            <div className="px-4 py-3">
              <code className="text-xs font-mono text-foreground break-all leading-relaxed select-all">
                {apiKey}
              </code>
            </div>
            <div className="border-t border-border px-4 py-2 flex justify-end bg-muted/50">
              <CopyButton value={apiKey} />
            </div>
          </div>

          {/* Security warning */}
          <div className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-300/80 leading-relaxed">
              This is the only time this key will be shown. Store it in a password manager or as
              an environment secret. Losing it means generating a new one.
            </p>
          </div>

          {/* Usage hint */}
          <div className="rounded-lg border border-border bg-muted/20 px-4 py-3">
            <p className="text-[11px] text-muted-foreground mb-1.5 flex items-center gap-1.5">
              <Terminal className="w-3 h-3" />
              Usage
            </p>
            <code className="text-[11px] font-mono text-muted-foreground">
              Authorization: Bearer <span className="text-foreground">{'<your-key>'}</span>
            </code>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={onClose} variant="outline" size="sm" className="h-8 text-xs">
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Generate key name modal
function GenerateKeyModal({
  open,
  onClose,
  onGenerate,
  generating,
}: {
  open: boolean
  onClose: () => void
  onGenerate: (name: string) => void
  generating: boolean
}) {
  const [name, setName] = useState('')
  const handleSubmit = () => {
    if (!name.trim()) return
    onGenerate(name.trim())
    setName('')
  }
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-base">New API key</DialogTitle>
          <DialogDescription>
            Give it a name so you know where it is used.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="key-name" className="text-xs text-muted-foreground">Key name</Label>
          <Input
            id="key-name"
            placeholder="e.g. Claude Desktop, CI/CD, Local dev"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            autoFocus
            className="h-9 text-sm"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose} className="h-8 text-xs">Cancel</Button>
          <Button size="sm" onClick={handleSubmit} disabled={!name.trim() || generating} className="h-8 text-xs gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            {generating ? 'Generating...' : 'Generate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


// -- Main page component --

export function APIKeysPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const token = session?.access_token || ''

  const [generateOpen, setGenerateOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generatedKey, setGeneratedKey] = useState<string | null>(null)
  const [revoking, setRevoking] = useState<string | null>(null)
  const [revokeTarget, setRevokeTarget] = useState<APIKey | null>(null)

  const { data: keys = [], isLoading, isError } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => fetchKeys(token),
    enabled: !!token,
  })

  const handleGenerate = async (name: string) => {
    if (!token) return
    setGenerating(true)
    try {
      const res = await fetch(`${API_URL}/keys/generate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to generate key')
      }
      const data = await res.json()
      setGenerateOpen(false)
      setGeneratedKey(data.api_key)
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to generate key')
    } finally {
      setGenerating(false)
    }
  }

  const handleRevoke = async () => {
    if (!token || !revokeTarget) return
    setRevoking(revokeTarget.id)
    setRevokeTarget(null)
    try {
      const res = await fetch(`${API_URL}/keys/${revokeTarget.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to revoke key')
      toast.success('API key revoked')
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    } catch {
      toast.error('Failed to revoke key')
    } finally {
      setRevoking(null)
    }
  }

  const activeKeys = keys.filter((k) => k.active)

  if (isLoading) return <APIKeysSkeleton />

  if (isError) {
    return (
      <div className="flex items-center justify-center min-h-[300px] text-muted-foreground text-sm">
        Failed to load API keys.
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-4xl">

      {/* Header -- matches UsagePage pattern exactly */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
            <Key className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">API Keys</h1>
            <p className="text-sm text-muted-foreground">
              Authenticate MCP, Claude Desktop, and direct API requests
            </p>
          </div>
        </div>
        <Button
          size="sm"
          onClick={() => setGenerateOpen(true)}
          disabled={activeKeys.length >= 5}
          className="gap-2 h-9 text-sm shrink-0"
        >
          <Plus className="w-4 h-4" />
          Generate key
          {activeKeys.length >= 5 && <span className="text-xs opacity-60">(limit reached)</span>}
        </Button>
      </div>

      {/* Security callout */}
      <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/20 px-4 py-3.5">
        <Shield className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
        <div>
          <p className="text-xs font-medium text-foreground">Keep your keys secure</p>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            API keys grant full account access. Never commit them to source control.
            Use environment variables or a secrets manager.
          </p>
        </div>
      </div>


      {/* Keys table or empty state */}
      {keys.length === 0 ? (
        <div className="rounded-lg border border-border">
          <EmptyState onGenerate={() => setGenerateOpen(true)} />
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          {/* Column headers */}
          <div className="grid gap-4 px-4 py-2.5 bg-muted/40 border-b border-border grid-cols-[1fr_200px_80px_110px_120px]">
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Name</span>
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Key</span>
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Tier</span>
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Last used</span>
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider text-right">Status</span>
          </div>

          {/* Rows */}
          {keys.map((k) => (
            <KeyRow
              key={k.id}
              apiKey={k}
              onRevoke={() => setRevokeTarget(k)}
              revoking={revoking === k.id}
            />
          ))}

          {/* Footer summary */}
          <div className="px-4 py-2.5 border-t border-border bg-muted/20 flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">
              {activeKeys.length} active
              {activeKeys.length !== keys.length && ` / ${keys.length} total`}
            </span>
            <span className="text-[11px] text-muted-foreground/50">
              {5 - activeKeys.length} key{5 - activeKeys.length !== 1 ? 's' : ''} remaining
            </span>
          </div>
        </div>
      )}

      {/* Modals */}
      <GenerateKeyModal
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        onGenerate={handleGenerate}
        generating={generating}
      />

      <NewKeyRevealModal
        apiKey={generatedKey}
        onClose={() => setGeneratedKey(null)}
      />

      <AlertDialog open={!!revokeTarget} onOpenChange={(open) => !open && setRevokeTarget(null)}>
        <AlertDialogContent className="max-w-sm">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-base">Revoke key</AlertDialogTitle>
            <AlertDialogDescription>
              Revoke <span className="font-medium text-foreground">{revokeTarget?.name}</span>?
              Any services using this key will lose access immediately. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="h-8 text-xs">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRevoke}
              className="h-8 text-xs bg-destructive hover:bg-destructive/90 text-destructive-foreground"
            >
              Revoke key
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </div>
  )
}
