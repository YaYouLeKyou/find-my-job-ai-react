/**
 * Badge Component - Visual indicator for job attributes
 * Features:
 * - Multiple types (location, contract, salary, experience)
 * - Consistent styling
 * - Accessible color contrast
 * - Responsive design
 */
import React from 'react';

interface BadgeProps {
  type: 'location' | 'contract' | 'salary' | 'experience' | 'skill';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ type, children, className = '' }) => {
  // Type-specific styling
  const typeClasses = {
    location: 'bg-blue-100 text-blue-800',
    contract: 'bg-green-100 text-green-800',
    salary: 'bg-purple-100 text-purple-800',
    experience: 'bg-yellow-100 text-yellow-800',
    skill: 'bg-gray-100 text-gray-700'
  };

  // Icon mapping
  const typeIcons = {
    location: '📍',
    contract: '📄',
    salary: '💰',
    experience: '🎓',
    skill: '✨'
  };

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${typeClasses[type]} ${className}`}>
      <span className="mr-1">{typeIcons[type]}</span>
      {children}
    </span>
  );
};

export default Badge;