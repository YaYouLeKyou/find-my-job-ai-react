/**
 * StatCard Component - Reusable statistic card for dashboards
 * Features:
 * - Clean design with icon support
 * - Trend indicator (up/down)
 * - Responsive layout
 * - Accessible color contrast
 */
import React from 'react';

interface StatCardProps {
  title: string;
  value: number | string;
  trend?: string;
  icon?: string;
  color?: 'blue' | 'green' | 'red' | 'purple';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  trend,
  icon = '📊',
  color = 'blue'
}) => {
  // Color mapping
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-800',
    purple: 'bg-purple-100 text-purple-800'
  };

  // Determine trend icon and color
  const trendIcon = trend && (trend.startsWith('+') || trend.startsWith('-'))
    ? trend.startsWith('+') ? '↑' : '↓'
    : null;
  const trendColor = trend && trend.startsWith('+') ? 'text-green-600' : 'text-red-600';

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-2xl ${colorClasses[color]}`}>
          {icon}
        </div>
        {trend && (
          <span className={`text-sm font-medium ${trendColor}`}>
            {trendIcon} {trend.replace(/^[+-]/, '')}
          </span>
        )}
      </div>

      <div className="mb-2">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        <h3 className="text-sm font-medium text-gray-600 mt-1">{title}</h3>
      </div>
    </div>
  );
};

export default StatCard;