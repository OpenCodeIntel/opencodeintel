import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  MiniMap,
} from 'reactflow'
import dagre from 'dagre'
import 'reactflow/dist/style.css'
import { useDependencyGraph } from '../hooks/useCachedQuery'

interface DependencyGraphProps {
  repoId: string
  apiUrl: string
  apiKey: string
}

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 40 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 180, height: 60 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    node.position = {
      x: nodeWithPosition.x - 90,
      y: nodeWithPosition.y - 30,
    }
  })

  return { nodes, edges }
}

export function DependencyGraph({ repoId, apiUrl, apiKey }: DependencyGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [metrics, setMetrics] = useState<any>(null)
  const [filterCritical, setFilterCritical] = useState(false)
  const [minDeps, setMinDeps] = useState(0)
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null)
  const [allNodes, setAllNodes] = useState<Node[]>([])
  const [allEdges, setAllEdges] = useState<Edge[]>([])

  // Use cached query for dependencies
  const { data, isLoading: loading, isFetching } = useDependencyGraph({ 
    repoId, 
    apiKey 
  })

  // Process data when it arrives
  useEffect(() => {
    if (data) {
      processGraphData(data)
    }
  }, [data])

  useEffect(() => {
    if (allNodes.length > 0) {
      applyFilters()
    }
  }, [filterCritical, minDeps, allNodes, allEdges])

  const applyFilters = () => {
    let filteredNodes = [...allNodes]
    let filteredEdges = [...allEdges]

    if (filterCritical || minDeps > 0) {
      const threshold = minDeps || 3
      filteredNodes = allNodes.filter((node: any) => 
        (node.data.imports || 0) >= threshold ||
        allEdges.some(e => e.target === node.id)
      )
      
      const nodeIds = new Set(filteredNodes.map(n => n.id))
      filteredEdges = allEdges.filter(e => 
        nodeIds.has(e.source) && nodeIds.has(e.target)
      )
    }

    const { nodes: layoutedNodes, edges: layoutedEdges } = 
      getLayoutedElements(filteredNodes, filteredEdges)
    
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }

  const processGraphData = (data: any) => {
    const flowNodes: Node[] = data.nodes.map((node: any) => {
      const fileName = node.label || node.id.split('/').pop()
      const fullPath = node.id
      const importCount = node.import_count || node.imports || 0
      
      return {
        id: node.id,
        type: 'default',
        data: { 
          label: (
            <div title={fullPath} style={{ cursor: 'pointer' }}>
              <div style={{ fontWeight: 600, fontSize: '11px', marginBottom: '4px' }}>
                {fileName}
              </div>
              {importCount > 0 && (
                <div style={{ fontSize: '9px', opacity: 0.8 }}>
                  {importCount} imports
                </div>
              )}
            </div>
          ),
          language: node.language,
          imports: importCount
        },
        position: { x: 0, y: 0 },
        style: {
          background: getLanguageColor(node.language),
          color: 'white',
          border: '2px solid #3b82f6',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '11px',
          fontFamily: 'monospace',
          width: 180,
          height: 60
        }
      }
    })
    
    const flowEdges: Edge[] = data.edges.map((edge: any) => ({
      id: `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      animated: false,
      style: { stroke: '#4b5563', strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#4b5563',
      },
    }))
    
    setAllNodes(flowNodes)
    setAllEdges(flowEdges)
    setMetrics(data.metrics)
    
    const { nodes: layoutedNodes, edges: layoutedEdges } = 
      getLayoutedElements(flowNodes, flowEdges)
    
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }

  const handleNodeClick = useCallback((event: any, node: Node) => {
    setHighlightedNode(node.id)
    
    const connectedNodeIds = new Set<string>()
    connectedNodeIds.add(node.id)
    
    allEdges.forEach(edge => {
      if (edge.source === node.id) connectedNodeIds.add(edge.target)
      if (edge.target === node.id) connectedNodeIds.add(edge.source)
    })
    
    setNodes(nodes =>
      nodes.map(n => ({
        ...n,
        style: {
          ...n.style,
          opacity: connectedNodeIds.has(n.id) ? 1 : 0.3,
          border: n.id === node.id ? '3px solid #ef4444' : n.style?.border
        }
      }))
    )
    
    setEdges(edges =>
      edges.map(e => ({
        ...e,
        style: {
          ...e.style,
          opacity: e.source === node.id || e.target === node.id ? 1 : 0.1,
          strokeWidth: e.source === node.id || e.target === node.id ? 2.5 : 1.5
        }
      }))
    )
  }, [allEdges])

  const resetHighlight = () => {
    setHighlightedNode(null)
    setNodes(nodes =>
      nodes.map(n => ({
        ...n,
        style: { ...n.style, opacity: 1, border: '2px solid #3b82f6' }
      }))
    )
    setEdges(edges =>
      edges.map(e => ({
        ...e,
        style: { ...e.style, opacity: 1, strokeWidth: 1.5 }
      }))
    )
  }

  const getLanguageColor = (language: string) => {
    const colors: any = {
      'python': '#3776ab',
      'javascript': '#f7df1e',
      'typescript': '#3178c6',
      'unknown': '#6b7280'
    }
    return colors[language] || colors.unknown
  }

  if (loading) {
    return (
      <div className="p-12 text-center">
        <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Building dependency graph...</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Total Files</div>
          <div className="text-3xl font-bold text-white">{allNodes.length}</div>
        </div>
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Dependencies</div>
          <div className="text-3xl font-bold text-blue-400">{edges.length}</div>
        </div>
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Avg per File</div>
          <div className="text-3xl font-bold text-white">
            {metrics?.avg_dependencies?.toFixed(1) || 0}
          </div>
        </div>
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <div className="text-sm text-gray-400 mb-1">Showing</div>
          <div className="text-3xl font-bold text-green-400">{nodes.length}</div>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filterCritical}
              onChange={(e) => setFilterCritical(e.target.checked)}
              className="w-4 h-4 bg-white/5 border-white/10 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-300">Show only critical files (≥3 deps)</span>
          </label>
          
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-300">Min dependencies:</label>
            <input
              type="range"
              min="0"
              max="10"
              value={minDeps}
              onChange={(e) => setMinDeps(Number(e.target.value))}
              className="w-32 accent-blue-500"
            />
            <span className="text-sm font-mono text-white">{minDeps}</span>
          </div>

          {highlightedNode && (
            <button
              onClick={resetHighlight}
              className="text-sm px-3 py-1.5 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 border border-red-500/20 transition-colors"
            >
              Clear highlight
            </button>
          )}
        </div>
      </div>

      {/* Most Critical Files */}
      {metrics?.most_critical_files && metrics.most_critical_files.length > 0 && (
        <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
          <h3 className="text-sm font-semibold mb-3 text-white">Most Critical Files</h3>
          <div className="space-y-2">
            {metrics.most_critical_files.slice(0, 5).map((item: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span className="font-mono text-gray-300 truncate flex-1">
                  {item.file.split('/').slice(-2).join('/')}
                </span>
                <span className="ml-2 px-2 py-0.5 text-xs bg-red-500/10 text-red-400 border border-red-500/20 rounded">
                  {item.dependents} dependents
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl overflow-hidden" style={{ height: '700px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onPaneClick={resetHighlight}
          fitView
          attributionPosition="bottom-left"
          minZoom={0.1}
          maxZoom={2}
        >
          <Background color="#1f1f23" gap={16} />
          <Controls className="!bg-[#111113] !border-white/10 !rounded-lg [&>button]:!bg-[#111113] [&>button]:!border-white/10 [&>button]:!text-gray-400 [&>button:hover]:!bg-white/10" />
          <MiniMap 
            nodeColor={(node) => {
              const style = node.style as any
              return style?.background || '#6b7280'
            }}
            maskColor="rgba(0, 0, 0, 0.5)"
            className="!bg-[#111113] !border-white/10"
          />
        </ReactFlow>
      </div>

      {/* Legend */}
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-3 text-white">Graph Legend</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: '#3776ab' }} />
            <span className="text-gray-400">Python</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: '#3178c6' }} />
            <span className="text-gray-400">TypeScript</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: '#f7df1e' }} />
            <span className="text-gray-400">JavaScript</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1 h-4 bg-blue-500" />
            <span className="text-gray-400">Dependency</span>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-white/5 text-xs text-gray-500">
          💡 Click any node to highlight its dependencies • Drag to pan • Scroll to zoom
        </div>
      </div>
    </div>
  )
}
