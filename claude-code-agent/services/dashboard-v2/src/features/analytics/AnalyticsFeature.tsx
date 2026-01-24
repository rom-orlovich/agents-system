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
  const [timeRange, setTimeRange] = useState<number>(7);
  const { trendData, agentData, isLoading, error } = useAnalyticsData(timeRange);
  const [hoverDate, setHoverDate] = useState<string | null>(null);

  if (isLoading) return <div className="p-12 text-center font-heading text-blue-400 animate-pulse">INITIALIZING_ANALYTICS_PROTOCOL...</div>;
  if (error) return <div className="p-8 text-red-500 font-heading border border-red-500/20 bg-red-900/10">SYSTEM_FAILURE: {error}</div>;

  const rangeLabel = timeRange === 1 ? "24H" : `${timeRange}D`;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-12">
      {/* HUD Header */}
      <div className="panel flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3">
             <h1 className="text-xl md:text-2xl font-heading font-bold tracking-wider text-text-main dark:text-dark-text">
               SYSTEM_ANALYTICS
             </h1>
          </div>
          <p className="text-xs font-mono text-gray-500 mt-2 flex items-center gap-2">
            REAL_TIME_MONITORING 
            <span className="opacity-30">//</span> 
            NODE: ALPHA_7 
            {hoverDate && (
              <span className="ml-2 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-[10px] font-bold">
                DATE: {hoverDate}
              </span>
            )}
          </p>
        </div>
        
        <div className="flex flex-col items-start md:items-end gap-3 w-full md:w-auto">
          {/* Timeframe Selector */}
          <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700">
            {[1, 7, 30].map((days) => (
              <button
                key={days}
                onClick={() => setTimeRange(days)}
                className={`px-3 py-1 text-[10px] font-heading font-medium rounded transition-all ${
                  timeRange === days
                    ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm"
                    : "text-gray-500 hover:text-gray-900 dark:hover:text-gray-300"
                }`}
              >
                {days === 1 ? "24H" : `${days}D`}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
             <div className="px-2 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold border border-emerald-200 dark:border-emerald-800 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                ONLINE
             </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* CHART 1: BURN RATE (Cost) */}
        <section className="panel group min-h-[400px]" data-label="FINANCIAL_TELEMETRY">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-blue-500 transition-colors">BURN_RATE_TREND [{rangeLabel}]</h2>
             <div className="text-xs font-mono text-gray-500">AVG: --/day</div>
          </div>
          
          <div className="h-[250px] md:h-[300px] w-full" style={{ minHeight: '250px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} onMouseMove={(e: any) => e.activeLabel && setHoverDate(e.activeLabel)} onMouseLeave={() => setHoverDate(null)}>
                <defs>
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={localStorage.theme === 'dark' ? '#334155' : '#e2e8f0'} opacity={0.5} />
                <XAxis dataKey="date" hide />
                <YAxis 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fontSize: 10, fill: "#94a3b8" }} 
                   tickFormatter={(val) => `$${val}`}
                   width={40}
                 />
                <Tooltip content={<CyberTooltip />} cursor={{ stroke: '#3B82F6', strokeWidth: 1, strokeDasharray: '5 5' }} />
                <Area 
                  type="monotone" 
                  dataKey="cost" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorCost)" 
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* CHART 2: TOKEN FLUX (Bar) */}
        <section className="panel group min-h-[400px]" data-label="TOKEN_THROUGHPUT">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-amber-400 transition-colors">TOKEN_CONSUMPTION [{rangeLabel}]</h2>
             <div className="text-xs font-mono text-gray-500">TOTAL: --</div>
          </div>

          <div className="h-[250px] md:h-[300px] w-full" style={{ minHeight: '250px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData} onMouseMove={(e: any) => e.activeLabel && setHoverDate(e.activeLabel)} onMouseLeave={() => setHoverDate(null)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={localStorage.theme === 'dark' ? '#334155' : '#e2e8f0'} opacity={0.5} />
                <XAxis dataKey="date" hide />
                <Tooltip content={<CyberTooltip />} cursor={{ fill: localStorage.theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }} />
                <Bar dataKey="tokens" fill="#F97316" radius={[2, 2, 0, 0]} animationDuration={1500} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* CHART 3: LATENCY (Composed) */}
        <section className="panel group min-h-[400px]" data-label="NETWORK_LATENCY">
          <div className="flex justify-between items-center mb-6">
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-emerald-400 transition-colors">SYSTEM_LATENCY [{rangeLabel}]</h2>
             <div className="text-xs font-mono text-gray-500">AVG: --ms</div>
          </div>

          <div className="h-[250px] md:h-[300px] w-full" style={{ minHeight: '250px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} onMouseMove={(e: any) => e.activeLabel && setHoverDate(e.activeLabel)} onMouseLeave={() => setHoverDate(null)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={localStorage.theme === 'dark' ? '#334155' : '#e2e8f0'} opacity={0.5} />
                <XAxis dataKey="date" hide />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} width={30} />
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
             <h2 className="text-sm font-heading text-gray-400 group-hover:text-purple-400 transition-colors">AGENT_LEADERBOARD [{rangeLabel}]</h2>
             <div className="text-xs font-mono text-gray-500">ACTIVE: {agentData?.length || 0}</div>
          </div>

          <div className="h-[300px] w-full" style={{ minHeight: '300px' }}>
             <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agentData} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={localStorage.theme === 'dark' ? '#334155' : '#e2e8f0'} opacity={0.5} />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false}
                  tick={{ fontSize: 9, fill: "#94A3B8", fontFamily: "Fira Code" }} 
                  width={100}
                />
                <Tooltip content={<CyberTooltip />} cursor={{ fill: localStorage.theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }} />
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
