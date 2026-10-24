"use client";

import React, { useMemo } from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

interface AxisData {
  axis_id: number | string;
  name: string;
  value: number; // 0-100 score
  domain: string;
}

interface BiologicalRadarProps {
  data: AxisData[];
  onAxisClick?: (axis: AxisData) => void;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-700 p-3 rounded-xl shadow-2xl backdrop-blur-md bg-opacity-90">
        <p className="text-primary-custom font-bold text-xs uppercase tracking-wider mb-1">{data.domain}</p>
        <p className="text-white font-bold text-sm mb-1">{data.name}</p>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary-custom" 
              style={{ width: `${data.value}%` }}
            ></div>
          </div>
          <span className="text-white font-mono text-xs">{data.value}</span>
        </div>
      </div>
    );
  }
  return null;
};

export default function BiologicalRadar({ data, onAxisClick }: BiologicalRadarProps) {
  // Group data by domain for coloring or other logic
  const chartData = useMemo(() => {
    return data.map(item => ({
      ...item,
      shortName: `Ax${item.axis_id}`,
    }));
  }, [data]);

  return (
    <div className="w-full h-[500px] md:h-[600px] relative">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
          <PolarGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <PolarAngleAxis 
            dataKey="shortName" 
            tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }}
          />
          <PolarRadiusAxis 
            angle={90} 
            domain={[0, 100]} 
            tick={false} 
            axisLine={false} 
          />
          <Radar
            name="Patient Status"
            dataKey="value"
            stroke="#0ea5e9"
            fill="#0ea5e9"
            fillOpacity={0.3}
            dot={{ r: 3, fill: '#0ea5e9', strokeWidth: 2, stroke: '#fff' }}
            activeDot={{ r: 5, fill: '#0ea5e9', strokeWidth: 2, stroke: '#fff' }}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
      
      {/* HUD Overlays */}
      <div className="absolute top-0 left-0 p-4 pointer-events-none">
        <div className="bg-white/80 backdrop-blur-md border border-slate-100 p-4 rounded-2xl shadow-sm">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">System Status</h4>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-sm font-bold text-slate-700 font-mono tracking-tighter">AI ENGINE ACTIVE</span>
          </div>
        </div>
      </div>

      <div className="absolute bottom-0 right-0 p-4 pointer-events-none text-right">
        <p className="text-[10px] font-bold text-slate-300 uppercase tracking-[0.2em]">TSPI MiHealth Radar v1.0</p>
      </div>
    </div>
  );
}
