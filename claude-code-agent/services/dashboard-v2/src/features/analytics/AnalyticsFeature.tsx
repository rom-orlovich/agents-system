import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAnalyticsData } from "./hooks/useAnalyticsData";

const COLORS = ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"];

export function AnalyticsFeature() {
  const { costData, performanceData, isLoading, error } = useAnalyticsData();

  if (isLoading) return <div className="p-8 text-center font-heading">ANALYZING_DATA...</div>;
  if (error) return <div className="p-8 text-red-500 font-heading">ERROR: {error}</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <section className="panel h-[450px]" data-label="COST_TREND_30D">
        <h2 className="text-sm mb-6 font-heading text-gray-400">BURN_RATE_OVER_TIME</h2>
        <div className="h-[350px] w-full relative">
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <AreaChart data={costData}>
              <defs>
                <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.5} />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: "#94A3B8" }}
                dy={10}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: "#94A3B8" }}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(255, 255, 255, 0.9)",
                  border: "1px solid #E2E8F0",
                  fontSize: "10px",
                  fontFamily: "Fira Code",
                  borderRadius: "4px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
                formatter={(value: any) => [`$${(Number(value) || 0).toFixed(4)}`, "COST"]}
              />
              <Area
                type="monotone"
                dataKey="cost"
                stroke="#3B82F6"
                fillOpacity={1}
                fill="url(#colorCost)"
                strokeWidth={2}
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel h-[450px]" data-label="AGENT_EFFICIENCY">
        <h2 className="text-sm mb-6 font-heading text-gray-400">COMPUTE_DISTRIBUTION_BY_AGENT</h2>
        <div className="h-[350px] w-full relative">
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <BarChart data={performanceData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0" />
              <XAxis
                type="number"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: "#94A3B8" }}
              />
              <YAxis
                dataKey="name"
                type="category"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: "#94A3B8", fontFamily: "Fira Code" }}
                width={120}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #E2E8F0",
                  fontSize: "12px",
                  fontFamily: "Fira Code",
                }}
              />
              <Bar dataKey="cost" radius={[0, 4, 4, 0]}>
                {performanceData?.map((item: { name: string; cost: number }, index: number) => (
                  <Cell key={`cell-${item.name}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
