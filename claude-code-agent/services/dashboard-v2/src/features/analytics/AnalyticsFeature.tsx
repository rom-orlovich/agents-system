import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { useAnalyticsData } from "./hooks/useAnalyticsData";
import { useState } from "react";

// Cyber Palette
const COLORS = [
  "#3B82F6", // Blue
  "#F97316", // Orange (CTA)
  "#10B981", // Emerald
  "#6366F1", // Indigo
  "#EC4899", // Pink (rare accent)
];

// Cyber Palette

const CyberTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900/95 border border-blue-500/30 p-3 shadow-xl backdrop-blur-md rounded-none min-w-[150px]">
        <div className="text-[10px] text-gray-400 font-mono mb-2 border-b border-gray-700 pb-1">
          TIMESTAMP: {label}
        </div>
        {payload.map((p: any, i: number) => (
          <div key={i} className="flex justify-between items-center text-xs font-mono my-1">
            <span style={{ color: p.color }}>{p.name.toUpperCase()}:</span>
            <span className="text-white ml-2">
              {p.name === "cost" ? "$" : ""}
              {p.value.toLocaleString()}
              {p.name === "latency" ? "ms" : ""}
            </span>
          </div>
        ))}
        {/* Fake decorative hex code */}
        <div className="text-[8px] text-gray-600 mt-2 text-right">0x{Math.floor(Math.random()*16777215).toString(16).toUpperCase()}</div>
      </div>
    );
  }
  return null;
};

export function AnalyticsFeature() {
  const { trendData, agentData, isLoading, error } = useAnalyticsData();
  const [hoverDate, setHoverDate] = useState<string | null>(null);

  if (isLoading) return <div className="p-12 text-center font-heading text-blue-400 animate-pulse">INITIALIZING_ANALYTICS_PROTOCOL...</div>;
  if (error) return <div className="p-8 text-red-500 font-heading border border-red-500/20 bg-red-900/10">SYSTEM_FAILURE: {error}</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-12">
      {/* HUD Header */}
      <div className="relative border-y border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-6 mb-8 backdrop-blur-sm">
        {/* Decorative Corners */}
        <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-blue-500 dark:border-blue-400" />
        <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-blue-500 dark:border-blue-400" />
        <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-blue-500 dark:border-blue-400" />
        <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-blue-500 dark:border-blue-400" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-2 h-8 bg-blue-600 dark:bg-blue-500" />
              <h1 className="text-3xl md:text-4xl font-heading font-black tracking-widest text-slate-900 dark:text-white">
                SYSTEM_ANALYTICS
              </h1>
            </div>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-2 pl-5 flex items-center gap-2">
              <span className="opacity-50">///</span> 
              REAL_TIME_MONITORING 
              <span className="opacity-50">//</span> 
              NODE: ALPHA_7 
              {hoverDate && (
                <span className="ml-2 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-none border border-blue-200 dark:border-blue-800 animate-pulse font-bold">
                  DATE: {hoverDate}
                </span>
              )}
            </p>
          </div>
          
          <div className="flex gap-3 pl-5 md:pl-0">
            <div className="flex flex-col items-end">
              <div className="flex gap-2 mb-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="h-2 w-2 rounded-full bg-emerald-500/50" />
                <span className="h-2 w-2 rounded-full bg-emerald-500/20" />
              </div>
              <div className="flex gap-3 text-[10px] font-heading tracking-wider">
                <div className="bg-slate-200 dark:bg-slate-800 px-3 py-1.5 text-slate-600 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
                  STATUS: ONLINE
                </div>
                <div className="bg-orange-50 dark:bg-orange-900/20 px-3 py-1.5 text-orange-600 dark:text-orange-400 border border-orange-200 dark:border-orange-500/30 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-orange-500 rounded-sm animate-ping" />
                  LIVE_STREAMING
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* CHART 1: BURN RATE (Cost) */}
        <section className="panel group min-h-[400px]" data-label="FINANCIAL_TELEMETRY">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-blue-400 transition-colors">BURN_RATE_TREND [30D]</h2>
             <div className="text-xs font-mono text-gray-500">AVG: $3.42/day</div>
          </div>
          
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} onMouseMove={(e: any) => e.activeLabel && setHoverDate(e.activeLabel)}>
                <defs>
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1e293b" />
                <XAxis dataKey="date" hide />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 10, fill: "#64748b" }} 
                  tickFormatter={(val) => `$${val}`}
                  width={30}
                />
                <Tooltip content={<CyberTooltip />} cursor={{ stroke: '#3B82F6', strokeWidth: 1, strokeDasharray: '5 5' }} />
                <Area 
                  type="monotone" 
                  dataKey="cost" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorCost)" 
                  animationDuration={2000}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* CHART 2: TOKEN FLUX (Bar) */}
        <section className="panel group min-h-[400px]" data-label="TOKEN_THROUGHPUT">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-amber-400 transition-colors">TOKEN_CONSUMPTION_RATE</h2>
             <div className="text-xs font-mono text-gray-500">TOTAL: 1.2M</div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1e293b" />
                <XAxis dataKey="date" hide />
                <Tooltip content={<CyberTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                <Bar dataKey="tokens" fill="#F97316" radius={[2, 2, 0, 0]} animationDuration={1500} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* CHART 3: LATENCY (Composed) */}
        <section className="panel group min-h-[400px]" data-label="NETWORK_LATENCY">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-emerald-400 transition-colors">SYSTEM_LATENCY_MS</h2>
             <div className="text-xs font-mono text-gray-500">P99: 412ms</div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1e293b" />
                <XAxis dataKey="date" hide />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#64748b" }} width={30} />
                <ReferenceLine y={300} stroke="#F97316" strokeDasharray="3 3" label={{ value: "THRESHOLD", fontSize: 10, fill: "#F97316" }} />
                <Tooltip content={<CyberTooltip />} />
                <Line 
                  type="stepAfter" 
                  dataKey="latency" 
                  stroke="#10B981" 
                  strokeWidth={2} 
                  dot={false}
                  activeDot={{ r: 4, fill: "#fff" }}
                  animationDuration={2000}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* CHART 4: AGENT EFFICIENCY (Radial/Bar) */}
        <section className="panel group min-h-[400px]" data-label="AGENT_PERFORMANCE">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-purple-400 transition-colors">AGENT_COMPUTE_DISTRIBUTION</h2>
             <div className="text-xs font-mono text-gray-500">ACTIVE_AGENTS: 5</div>
          </div>

          <div className="h-[300px] w-full">
             <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agentData} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false}
                  tick={{ fontSize: 9, fill: "#94A3B8", fontFamily: "Fira Code" }} 
                  width={100}
                />
                <Tooltip content={<CyberTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                <Bar dataKey="cost" radius={[0, 4, 4, 0]} barSize={20}>
                  {agentData?.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
                <Bar dataKey="efficiency" fill="#334155" radius={[0, 4, 4, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

      </div>
    </div>
  );
}
